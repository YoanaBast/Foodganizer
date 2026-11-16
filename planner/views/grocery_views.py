from planner.services.fridge_storage import get_fridge
from collections import OrderedDict

from django.core.paginator import Paginator
from django.db.models import Prefetch, Exists, OuterRef
from django.views import View
from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Subquery,
    Sum,
    F,
    FloatField,
    ExpressionWrapper,
    Case,
    When,
)
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit
from planner.helpers import convert_qty_to_unit, build_needed_dict, save_grocery_list, save_generation_history, build_preview_message
from planner.models import UserFridge, UserGroceryList, GroceryListGeneration, GroceryListGenerationItem, UserMealList
from recipes.models import Recipe, RecipeIngredient
from planner.helpers import *


class GenerateGroceryListView(View):
    template_name = 'planner/grocery/generate_grocery_list.html'


    def get_recipes(self, request, show_favs):
        from recipes.models import RecipeCategory
        from ingredients.models import IngredientDietaryTag

        search = request.GET.get('search', '')
        category = request.GET.get('category', '')
        tags = [t for t in request.GET.getlist('tag') if t]
        sort = request.GET.get('sort', '')

        kcal_subquery = (
            RecipeIngredient.objects
            .filter(recipe=OuterRef('pk'))
            .annotate(
                quantity_in_base=Case(
                    When(
                        unit__unit=F('ingredient__default_unit'),
                        then=F('quantity'),
                    ),
                    default=F('quantity') * F('unit__conversion_to_base'),
                    output_field=FloatField(),
                )
            )
            .annotate(
                contribution=ExpressionWrapper(
                    F('quantity_in_base')
                    * F('ingredient__base_quantity_kcal')
                    / F('ingredient__base_quantity'),
                    output_field=FloatField(),
                )
            )
            .values('recipe')
            .annotate(total=Sum('contribution'))
            .values('total')
        )

        recipes = (
            Recipe.objects
            .select_related('category')
            .prefetch_related(
                Prefetch(
                    'recipe_ingredient',
                    queryset=RecipeIngredient.objects.select_related(
                        'unit__unit',
                        'ingredient',
                    )
                )
            )
            .annotate(
                total_kcal=Coalesce(
                    Subquery(kcal_subquery, output_field=FloatField()),
                    0.0,
                ),
                kcal_per_serving_annotated=ExpressionWrapper(
                    F('total_kcal') / F('servings'),
                    output_field=FloatField(),
                ),
            )
        )

        if request.user.is_authenticated:
            recipes = recipes.annotate(
                is_fav=Exists(
                    Recipe.favourited_by.through.objects.filter(
                        recipe_id=OuterRef('pk'),
                        user_id=request.user.id,
                    )
                )
            )

            if show_favs:
                recipes = recipes.filter(
                    favourited_by=request.user
                )

        if search:
            recipes = recipes.filter(name__icontains=search)

        if category:
            recipes = recipes.filter(category_id=category)

        if tags:
            for tag_id in tags:
                recipes = recipes.exclude(
                    recipe_ingredient__in=RecipeIngredient.objects.exclude(
                        ingredient__dietary_tag__id=tag_id
                    )
                )

        if sort == 'kcal_asc':
            recipes = recipes.order_by(
                'kcal_per_serving_annotated'
            )

        elif sort == 'kcal_desc':
            recipes = recipes.order_by(
                '-kcal_per_serving_annotated'
            )

        elif sort == 'popular':
            recipes = recipes.annotate(
                fav_count=Count('favourited_by', distinct=True)
            ).order_by('-fav_count')

        else:
            recipes = recipes.order_by('name')

        return recipes

    def get_page_obj(self, request, recipes):
        return Paginator(recipes, 10).get_page(request.GET.get('page'))

    def get_filter_context(self, request):
        from recipes.models import RecipeCategory
        from ingredients.models import IngredientDietaryTag
        return {
            'search': request.GET.get('search', ''),
            'categories': RecipeCategory.objects.all().order_by('name'),
            'tags': IngredientDietaryTag.objects.all().order_by('name'),
            'selected_category': request.GET.get('category', ''),
            'selected_tags': [t for t in request.GET.getlist('tag') if t],
            'selected_sort': request.GET.get('sort', ''),
        }

    def get_grid(self, request):
        qs = (
            Recipe.objects
            .select_related('category')
            .prefetch_related('recipe_ingredient__ingredient__dietary_tag')
            .annotate(fav_count=Count('favourited_by', distinct=True))
        )
        if request.user.is_authenticated:
            qs = qs.annotate(
                is_fav=Exists(
                    Recipe.favourited_by.through.objects.filter(
                        recipe_id=OuterRef('pk'), user_id=request.user.id
                    )
                )
            ).order_by('-is_fav', '-fav_count', 'name')
        else:
            qs = qs.order_by('-fav_count', 'name')

        grouped = OrderedDict()
        for rec in qs[:10]:
            sets = [{t.name for t in ri.ingredient.dietary_tag.all()}
                    for ri in rec.recipe_ingredient.all()]
            rec.tag_names = sorted(set.intersection(*sets)) if sets else []
            name = rec.category.name if rec.category else 'Other'
            grouped.setdefault(name, []).append(rec)
        return grouped

    def build_context(self, request, selected_recipes, show_favs):
        page_obj = self.get_page_obj(request, self.get_recipes(request, show_favs))
        context = {
            'grouped_recipes': self.get_grid(request),
            'page_obj': page_obj,
            'selected_recipes': selected_recipes,
            'show_favs': show_favs,
            'items': get_grocery_items(request),
        }
        context.update(self.get_filter_context(request))
        context.update(get_fridge_context(request))
        return context

    def get(self, request):
        show_favs = request.GET.get('favs') == '1'
        selected = list(dict.fromkeys(request.GET.getlist('recipes')))
        return render(request, self.template_name, self.build_context(request, selected, show_favs))

    def post(self, request):
        show_favs = request.GET.get('favs') == '1'
        recipe_ids = list(dict.fromkeys(request.POST.getlist('recipes')))

        if not recipe_ids:
            messages.warning(request, "No recipes selected!")
            return render(request, self.template_name, self.build_context(request, [], show_favs))

        selected_recipes_qs = Recipe.objects.filter(id__in=recipe_ids).prefetch_related(
            Prefetch(
                'recipe_ingredient',
                queryset=RecipeIngredient.objects.select_related('ingredient', 'unit__unit',
                                                                 'ingredient__default_unit')
            )
        )

        needed = build_needed_dict(selected_recipes_qs, request)
        final_needed = get_fridge(request).missing(needed)

        if not final_needed:
            messages.info(request, "You already have all the ingredients in your fridge!")
            return redirect('generate_grocery_list')

        if request.user.is_authenticated:
            save_grocery_list(request.user, final_needed)
            save_generation_history(request.user, final_needed)
        else:
            anon_grocery = request.session.get('anon_grocery', [])
            for data in final_needed.values():
                ing_id = data['ingredient'].id
                unit_id = data['unit'].id if data['unit'] else None
                existing = next(
                    (i for i in anon_grocery
                     if i['ingredient_id'] == ing_id and i['unit_id'] == unit_id), None)
                if existing:
                    existing['quantity'] += data['quantity']
                else:
                    anon_grocery.append({'ingredient_id': ing_id, 'unit_id': unit_id,
                                         'quantity': data['quantity']})
            request.session['anon_grocery'] = anon_grocery
            request.session.modified = True

        messages.success(request, build_preview_message(final_needed))
        return redirect('generate_grocery_list')

class RecipeBrowserView(GenerateGroceryListView):
    """The original recipe table, served as a partial for the 'More Recipes' button."""
    template_name = 'planner/grocery/_recipe_browser.html'
    http_method_names = ['get']

    def get(self, request):
        show_favs = request.GET.get('favs') == '1'
        page_obj = self.get_page_obj(request, self.get_recipes(request, show_favs))
        context = {
            'page_obj': page_obj,
            'recipes': page_obj.object_list,
            'selected_recipes': list(dict.fromkeys(request.GET.getlist('recipes'))),
            'show_favs': show_favs,
        }
        context.update(self.get_filter_context(request))
        return render(request, self.template_name, context)


class UserGroceryListView(View):
    template_name = 'planner/grocery/user_grocery_list.html'

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

            ingredient_ids = {
                item['ingredient_id']
                for item in anon_grocery
            }

            unit_ids = {
                item['unit_id']
                for item in anon_grocery
                if item.get('unit_id')
            }

            ingredients = Ingredient.objects.filter(
                id__in=ingredient_ids
            )

            units = MeasurementUnit.objects.filter(
                id__in=unit_ids
            )

            ingredient_map = {
                ingredient.id: ingredient
                for ingredient in ingredients
            }

            unit_map = {
                unit.id: unit
                for unit in units
            }

            resolved = []

            for index, item in enumerate(anon_grocery):
                ingredient = ingredient_map.get(item['ingredient_id'])

                if not ingredient:
                    continue

                unit = unit_map.get(item['unit_id'])

                resolved.append({
                    'index': index,
                    'ingredient': ingredient,
                    'unit': unit,
                    'quantity': item['quantity'],
                })

            items = resolved
            history_page_obj = None


        return render(request, self.template_name, {
                'items': items,
                'history': history_page_obj,
                'history_page_obj': history_page_obj,
            })


class DeleteGroceryItemView(View):
    def post(self, request, item_id):
        if request.user.is_authenticated:
            get_object_or_404(UserGroceryList, id=item_id, user=request.user).delete()
        return redirect_back(request, 'user_grocery_list')


class DeleteAnonGroceryItemView(View):
    def post(self, request, index):
        grocery = request.session.get('anon_grocery', [])
        if 0 <= index < len(grocery):
            grocery.pop(index)
            request.session['anon_grocery'] = grocery
            request.session.modified = True
        return redirect_back(request, 'user_grocery_list')


class AddGroceryToFridgeView(View):
    def post(self, request, item_id):
        if request.user.is_authenticated:
            item = get_object_or_404(UserGroceryList, id=item_id, user=request.user)
            UserFridge.objects.update_or_create(
                user=request.user,
                ingredient=item.ingredient,
                defaults={'quantity': item.quantity, 'unit': item.unit}
            )
            item.delete()
        return redirect_back(request, 'user_grocery_list')


class AddAnonGroceryToFridgeView(View):
    def post(self, request, index):
        grocery = request.session.get('anon_grocery', [])
        if 0 <= index < len(grocery):
            item = grocery[index]
            ingredient = get_object_or_404(Ingredient, id=item['ingredient_id'])
            unit = MeasurementUnit.objects.get(id=item['unit_id'])
            get_fridge(request).add(ingredient, item['quantity'], unit)
            grocery.pop(index)
            request.session['anon_grocery'] = grocery
            request.session.modified = True
        return redirect_back(request, 'user_grocery_list')


class AddAllGroceryToFridgeView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(
                request,
                "You must be logged in to do this."
            )
            return redirect('user_grocery_list')

        items = list(
            UserGroceryList.objects
            .filter(user=request.user)
            .select_related('ingredient', 'unit')
        )

        fridge_map = {
            item.ingredient_id: item
            for item in UserFridge.objects.filter(
                user=request.user
            )
        }

        to_create = []
        to_update = []

        for item in items:
            fridge_item = fridge_map.get(item.ingredient_id)

            if fridge_item:
                fridge_item.quantity = item.quantity
                fridge_item.unit = item.unit
                to_update.append(fridge_item)
            else:
                to_create.append(
                    UserFridge(
                        user=request.user,
                        ingredient=item.ingredient,
                        quantity=item.quantity,
                        unit=item.unit,
                    )
                )

        if to_create:
            UserFridge.objects.bulk_create(to_create)

        if to_update:
            UserFridge.objects.bulk_update(
                to_update,
                ['quantity', 'unit']
            )

        UserGroceryList.objects.filter(
            user=request.user
        ).delete()

        return redirect('user_grocery_list')


class AddAllAnonGroceryToFridgeView(View):
    def post(self, request):
        fridge = get_fridge(request)
        for item in request.session.get('anon_grocery', []):
            fridge.add_by_ids(item['ingredient_id'], item['quantity'], item['unit_id'])
        request.session['anon_grocery'] = []
        request.session.modified = True
        return redirect('user_grocery_list')

def calorie_tracker(request):
    return render(request, "planner/calendar.html")
