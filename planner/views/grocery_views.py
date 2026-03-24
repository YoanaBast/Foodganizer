from collections import OrderedDict

from django.core.paginator import Paginator
from django.db.models import Prefetch, Exists, OuterRef
from django.views import View

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit
from planner.helpers import convert_qty_to_unit, build_needed_dict, subtract_fridge, save_grocery_list, \
    save_generation_history, build_preview_message, get_or_create_fridge_item, get_or_create_anon_fridge_item, \
    subtract_anon_fridge
from planner.models import UserFridge, UserGroceryList, GroceryListGeneration, GroceryListGenerationItem, UserMealList
from recipes.models import Recipe, RecipeIngredient



class GenerateGroceryListView(View):
    template_name = 'planner/generate_grocery_list.html'

    def get_recipes(self, user, show_favs):
        recipes = Recipe.objects.prefetch_related(
            Prefetch('recipe_ingredient', queryset=RecipeIngredient.objects.select_related('unit', 'ingredient'))
        )
        if user and user.is_authenticated:
            recipes = recipes.annotate(
                is_fav=Exists(
                    Recipe.favourited_by.through.objects.filter(
                        recipe_id=OuterRef('pk'), user_id=user.id
                    )
                )
            )
            if show_favs:
                recipes = recipes.filter(favourited_by=user)
        return recipes.order_by('name')

    def get_page_obj(self, request, recipes):
        paginator = Paginator(recipes, 10)
        return paginator.get_page(request.GET.get('page'))

    def get(self, request):
        show_favs = request.GET.get('favs') == '1'
        recipes = self.get_recipes(request.user, show_favs)
        page_obj = self.get_page_obj(request, recipes)
        selected_recipes = list(dict.fromkeys(request.GET.getlist('recipes')))

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'recipes': page_obj.object_list,
            'selected_recipes': selected_recipes,
            'show_favs': show_favs,
        })

    def post(self, request):
        show_favs = request.GET.get('favs') == '1'
        recipes = self.get_recipes(request.user, show_favs)
        page_obj = self.get_page_obj(request, recipes)
        recipe_ids = list(dict.fromkeys(request.POST.getlist('recipes')))

        if not recipe_ids:
            messages.warning(request, "No recipes selected!")
            return render(request, self.template_name, {
                'page_obj': page_obj,
                'recipes': page_obj.object_list,
                'selected_recipes': [],
                'show_favs': show_favs,
            })

        selected_recipes_qs = Recipe.objects.filter(id__in=recipe_ids).prefetch_related(
            Prefetch(
                'recipe_ingredient',
                queryset=RecipeIngredient.objects.select_related('ingredient', 'unit__unit', 'ingredient__default_unit')
            )
        )

        for r in selected_recipes_qs:
            print(f"Recipe: {r.name}, ingredients: {list(r.recipe_ingredient.all())}")

        if request.user.is_authenticated:
            fridge_items = UserFridge.objects.filter(user=request.user).select_related('ingredient', 'unit')
            needed = build_needed_dict(selected_recipes_qs, request)
            final_needed = subtract_fridge(needed, fridge_items, request)
        else:
            fridge_items = UserFridge.objects.none()
            needed = build_needed_dict(selected_recipes_qs, request)
            final_needed = subtract_anon_fridge(needed, request)  # ← new helper
        print("NEEDED:", {k: v['total_qty'] for k, v in needed.items()})
        if not final_needed:
            print("FINAL:", {k: v['quantity'] for k, v in final_needed.items()})

            messages.info(request, "You already have all the ingredients in your fridge!")
            return redirect('generate_grocery_list')

        if request.user.is_authenticated:
            save_grocery_list(request.user, final_needed)
            save_generation_history(request.user, final_needed)
        else:
            # store in session for anon
            anon_grocery = request.session.get('anon_grocery', [])

            for data in final_needed.values():
                ing_id = data['ingredient'].id
                unit_id = data['unit'].id if data['unit'] else None
                qty = data['quantity']

                # find existing entry with same ingredient + unit
                existing = next(
                    (item for item in anon_grocery
                     if item['ingredient_id'] == ing_id and item['unit_id'] == unit_id),
                    None
                )
                if existing:
                    existing['quantity'] += qty
                else:
                    anon_grocery.append({
                        'ingredient_id': ing_id,
                        'unit_id': unit_id,
                        'quantity': qty,
                    })

            request.session['anon_grocery'] = anon_grocery
            request.session.modified = True

        messages.success(request, build_preview_message(final_needed))

        return redirect('user_grocery_list')


class UserGroceryListView(View):
    template_name = 'planner/user_grocery_list.html'

    def get_history_data(self, user):
        raw_history = GroceryListGeneration.objects.filter(user=user).prefetch_related(
            'items__ingredient', 'items__unit', 'items__recipe',
        )
        history_data = []
        for gen in raw_history:
            by_recipe = OrderedDict()
            for item in gen.items.all():
                recipe_name = item.recipe.name if item.recipe else "Unknown Recipe"
                if recipe_name not in by_recipe:
                    by_recipe[recipe_name] = []
                by_recipe[recipe_name].append(item)
            history_data.append({
                'created_at': gen.created_at,
                'by_recipe': by_recipe,
            })
        return history_data

    def get(self, request):
        if request.user.is_authenticated:
            items = UserGroceryList.objects.filter(user=request.user).select_related('ingredient', 'unit')
            history_page_obj = Paginator(self.get_history_data(request.user), 5).get_page(
                request.GET.get('history_page')
            )
        else:
            anon_grocery = request.session.get('anon_grocery', [])
            resolved = []
            for index, item in enumerate(anon_grocery):
                try:
                    resolved.append({
                        'index': index,
                        'ingredient': Ingredient.objects.get(id=item['ingredient_id']),
                        'unit': MeasurementUnit.objects.get(id=item['unit_id']) if item['unit_id'] else None,
                        'quantity': item['quantity'],
                    })
                except (Ingredient.DoesNotExist, MeasurementUnit.DoesNotExist):
                    continue
            items = resolved
            history_page_obj = None

        return render(request, self.template_name, {
            'items': items,
            'history': history_page_obj,
            'history_page_obj': history_page_obj,
        })


class DeleteGroceryItemView(View):
    def post(self, request, item_id):
        item = get_object_or_404(UserGroceryList, id=item_id)
        item.delete()
        return redirect('user_grocery_list')


class DeleteAnonGroceryItemView(View):
    def post(self, request, index):
        grocery = request.session.get('anon_grocery', [])
        if 0 <= index < len(grocery):
            grocery.pop(index)
            request.session['anon_grocery'] = grocery
            request.session.modified = True
        return redirect('user_grocery_list')


class AddGroceryToFridgeView(View):
    def post(self, request, item_id):
        item = get_object_or_404(UserGroceryList, id=item_id)
        UserFridge.objects.update_or_create(
            user=item.user,
            ingredient=item.ingredient,
            defaults={'quantity': item.quantity, 'unit': item.unit}
        )
        item.delete()
        return redirect('user_grocery_list')


class AddAnonGroceryToFridgeView(View):
    def post(self, request, index):
        grocery = request.session.get('anon_grocery', [])
        if 0 <= index < len(grocery):
            item = grocery[index]
            ingredient = get_object_or_404(Ingredient, id=item['ingredient_id'])
            unit = MeasurementUnit.objects.get(id=item['unit_id'])
            get_or_create_anon_fridge_item(request, ingredient, item['quantity'], unit)
            grocery.pop(index)
            request.session['anon_grocery'] = grocery
            request.session.modified = True
        return redirect('user_grocery_list')


class AddAllGroceryToFridgeView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to do this.")
            return redirect('user_grocery_list')

        items = UserGroceryList.objects.filter(user=request.user)
        for item in items:
            UserFridge.objects.update_or_create(
                user=request.user,
                ingredient=item.ingredient,
                defaults={'quantity': item.quantity, 'unit': item.unit}
            )
        items.delete()
        return redirect('user_grocery_list')


class AddAllAnonGroceryToFridgeView(View):
    def post(self, request):
        grocery = request.session.get('anon_grocery', [])
        for item in grocery:
            try:
                ingredient = Ingredient.objects.get(id=item['ingredient_id'])
                unit = MeasurementUnit.objects.get(id=item['unit_id'])
                get_or_create_anon_fridge_item(request, ingredient, item['quantity'], unit)
            except (Ingredient.DoesNotExist, MeasurementUnit.DoesNotExist):
                continue
        request.session['anon_grocery'] = []
        request.session.modified = True
        return redirect('user_grocery_list')


def calorie_tracker(request):
    return render(request, "planner/calendar.html")
