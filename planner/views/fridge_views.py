import json

from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from planner.forms import UserFridgeForm
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit
from planner.helpers import convert_qty_to_unit, build_needed_dict, subtract_fridge, save_grocery_list, \
    save_generation_history, build_preview_message, get_or_create_fridge_item, get_or_create_anon_fridge_item, \
    subtract_anon_fridge
from planner.models import UserFridge, UserGroceryList, GroceryListGeneration, GroceryListGenerationItem, UserMealList
from recipes.models import Recipe, RecipeIngredient

# Create your views here.


class ManageFridgeView(ListView):
    template_name = 'planner/manage_fridge.html'
    context_object_name = 'fridge'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserFridge.objects.filter(user=self.request.user).select_related('ingredient__category', 'unit')
        return UserFridge.objects.none()  # anon gets empty DB queryset, session handled in template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ingredients'] = Ingredient.objects.all()
        if not self.request.user.is_authenticated:
            anon_fridge = self.request.session.get('anon_fridge', [])
            resolved = []
            for index, item in enumerate(anon_fridge):
                try:
                    resolved.append({
                        'index': index,  # ← add this
                        'ingredient': Ingredient.objects.get(id=item['ingredient_id']),
                        'unit': MeasurementUnit.objects.get(id=item['unit_id']),
                        'quantity': item['quantity'],
                    })
                except (Ingredient.DoesNotExist, MeasurementUnit.DoesNotExist):
                    continue
            context['anon_fridge'] = resolved
        return context


class AddFridgeItemView(View):
    def post(self, request):
        ing_id = request.POST.get("ingredient_id")
        ingredient = get_object_or_404(Ingredient, id=ing_id)

        form = UserFridgeForm(request.POST)
        if not form.is_valid():
            messages.error(request, list(form.errors.values())[0][0])
            return redirect('manage_fridge')

        qty = form.cleaned_data['quantity']
        unit = form.cleaned_data['unit']

        if request.user.is_authenticated:
            get_or_create_fridge_item(request, ingredient, qty, unit)
        else:
            get_or_create_anon_fridge_item(request, ingredient, qty, unit)

        return redirect('manage_fridge')


class EditFridgeItemView(UpdateView):
    model = UserFridge
    form_class = UserFridgeForm
    template_name = 'planner/edit_fridge.html'
    pk_url_kwarg = 'item_id'
    success_url = reverse_lazy('manage_fridge')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = self.object
        context['ingredient_units'] = self.object.ingredient.measurement_units.select_related('unit').all()
        return context


class EditAnonFridgeItemView(View):

    def get(self, request, index):
        fridge = request.session.get('anon_fridge', [])
        print(fridge)
        if not (0 <= index < len(fridge)):
            return redirect('manage_fridge')

        item = fridge[index]

        ingredient = get_object_or_404(Ingredient, id=item['ingredient_id'])

        ingredient_units = (
            ingredient.measurement_units
            .select_related('unit')
            .all()
        )

        context = {
            'ingredient': ingredient,
            'quantity': item['quantity'],
            'unit_id': item['unit_id'],
            'ingredient_units': ingredient_units,
            'anon_index': index,
        }

        return render(request, 'planner/edit_fridge.html', context)

    def post(self, request, index):
        fridge = request.session.get('anon_fridge', [])

        if not (0 <= index < len(fridge)):
            return JsonResponse({'error': 'Invalid index'}, status=400)

        #  detect AJAX
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)

            fridge[index]['quantity'] = float(data.get('quantity'))
            fridge[index]['unit_id'] = int(data.get('unit_id'))

            request.session['anon_fridge'] = fridge
            request.session.modified = True

            return JsonResponse({'status': 'ok'})

        # fallback: normal form submit
        form = UserFridgeForm(request.POST)

        if form.is_valid():
            fridge[index]['quantity'] = form.cleaned_data['quantity']
            fridge[index]['unit_id'] = form.cleaned_data['unit'].id

            request.session['anon_fridge'] = fridge
            request.session.modified = True

        return redirect('manage_fridge')


class DeleteFridgeItemView(View):
    def post(self, request, fridge_id):
        if request.user.is_authenticated:
            item = get_object_or_404(UserFridge, id=fridge_id, user=request.user)
            item.delete()
        return redirect('manage_fridge')


class DeleteAnonFridgeItemView(View):
    def post(self, request, index):
        fridge = request.session.get('anon_fridge', [])
        if 0 <= index < len(fridge):
            fridge.pop(index)
            request.session['anon_fridge'] = fridge
        return redirect('manage_fridge')






"""
Older views:
"""

# def manage_fridge(request):
#     user, _ = User.objects.get_or_create(username="default")
#     fridge_list = UserFridge.objects.filter(user=user).select_related('ingredient__category', 'unit')
#     ingredients = Ingredient.objects.all()
#
#     paginator = Paginator(fridge_list, 10)  # 10 items per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     context = {
#         'fridge': page_obj,  # pass page_obj instead of full queryset
#         'ingredients': ingredients,
#         'page_obj': page_obj,  # for pagination controls
#     }
#
#     return render(request, 'planner/manage_fridge.html', context)


# def edit_fridge_item(request, item_id):
#     item = get_object_or_404(UserFridge, pk=item_id)
#
#     if request.method == 'POST':
#         form = UserFridgeForm(request.POST, instance=item)
#         if form.is_valid():
#             form.save()
#             return redirect('manage_fridge')
#     else:
#         form = UserFridgeForm(instance=item)
#
#     ingredient_units = item.ingredient.measurement_units.select_related('unit').all()
#
#     return render(request, 'planner/edit_fridge.html', {
#         'form': form,
#         'item': item,
#         'ingredient_units': ingredient_units,
#     })


# def delete_fridge_item(request, fridge_id):
#     user, _ = User.objects.get_or_create(username="default")
#     item = get_object_or_404(UserFridge, id=fridge_id, user=user)
#     if request.method == "POST":
#         item.delete()
#     return redirect('manage_fridge')


# def add_fridge_item(request):
#     if request.method == "POST":
#         user, _ = User.objects.get_or_create(username="default")
#
#         ing_id = request.POST.get("ingredient_id")
#         qty_raw = request.POST.get("quantity")
#         try:
#             qty = float(qty_raw)
#             if qty < 0.01:
#                 messages.error(request, 'Quantity must be at least 0.01.')
#                 return redirect('manage_fridge')
#         except (ValueError, TypeError):
#             messages.error(request, 'Please enter a valid quantity.')
#             return redirect('manage_fridge')
#
#         unit_id = request.POST.get("unit")
#
#         ingredient = Ingredient.objects.get(id=ing_id)
#         unit = MeasurementUnit.objects.get(id=unit_id)
#
#         # Merge-in all other fridge items of the same ingredient
#         from planner.models import UserFridge
#         from ingredients.models import IngredientMeasurementUnit
#
#         explanations = []
#
#         # Check for existing items in **any unit** of the same ingredient
#         items = UserFridge.objects.filter(user=user, ingredient=ingredient)
#         target_item = items.filter(unit=unit).first()
#
#         for item in items.exclude(id=getattr(target_item, "id", None)):
#             try:
#                 item_unit_conv = IngredientMeasurementUnit.objects.get(
#                     ingredient=ingredient, unit=item.unit
#                 )
#                 target_unit_conv = IngredientMeasurementUnit.objects.get(
#                     ingredient=ingredient, unit=unit
#                 )
#             except IngredientMeasurementUnit.DoesNotExist:
#                 explanations.append(f"Cannot convert {item.unit} → {unit}")
#                 continue
#
#             # Convert to target unit
#             qty_in_base = item.quantity * item_unit_conv.conversion_to_base
#             qty_in_target = qty_in_base / target_unit_conv.conversion_to_base
#
#             if target_item:
#                 target_item.quantity += qty_in_target
#                 target_item.save()
#             else:
#                 target_item = UserFridge.objects.create(
#                     user=user,
#                     ingredient=ingredient,
#                     quantity=qty_in_target,
#                     unit=unit
#                 )
#
#             explanations.append(
#                 f"{item.quantity} {item.unit} → {round(qty_in_target, 2)} {unit} added"
#             )
#
#             item.delete()
#
#         # Add the new quantity being submitted
#         if target_item:
#             target_item.quantity += qty
#             target_item.save()
#         else:
#             target_item = UserFridge.objects.create(
#                 user=user,
#                 ingredient=ingredient,
#                 quantity=qty,
#                 unit=unit
#             )
#
#     return redirect("manage_fridge")


# def meal_list(request):
#     user, _ = User.objects.get_or_create(username="default")
#     meals = UserMealList.objects.filter(user=user).select_related('recipe')
#
#     paginator = Paginator(meals, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     return render(request, "planner/meal_list.html", {
#         "page_obj": page_obj,
#     })


# def generate_grocery_list(request):
#     user, _ = User.objects.get_or_create(username="default")
#
#     show_favs = request.GET.get('favs') == '1'
#
#     recipes = Recipe.objects.annotate(
#         is_fav=Exists(
#             Recipe.favourited_by.through.objects.filter(
#                 recipe_id=OuterRef('pk'),
#                 user_id=user.id
#             )
#         )
#     ).prefetch_related(
#         Prefetch('recipe_ingredient', queryset=RecipeIngredient.objects.select_related('unit', 'ingredient'))
#     )
#
#     if show_favs:
#         recipes = recipes.filter(favourited_by=user)
#
#     recipes = recipes.order_by('name')
#
#     paginator = Paginator(recipes, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     selected_recipes = request.POST.getlist('recipes') or request.GET.getlist('recipes')
#     selected_recipes = list(dict.fromkeys(selected_recipes))
#
#     if request.method == "POST":
#         recipe_ids = request.POST.getlist('recipes')
#         recipe_ids = list(dict.fromkeys(recipe_ids))
#         selected_recipes = recipe_ids
#
#         if not recipe_ids:
#             messages.warning(request, "No recipes selected!")
#             return render(request, 'planner/generate_grocery_list.html', {
#                 'page_obj': page_obj,
#                 'recipes': page_obj.object_list,
#                 'selected_recipes': selected_recipes,
#                 'show_favs': show_favs,
#
#             })
#
#         selected_recipes_qs = Recipe.objects.filter(id__in=recipe_ids).prefetch_related(
#             'recipe_ingredient__ingredient',
#             'recipe_ingredient__unit'
#         )
#
#         # Build needed dict keyed by ingredient id, tracking which recipe each line came from
#         # needed[ing_id] = { ingredient, unit, recipes: { recipe: qty_in_base } }
#         needed = {}
#
#         for rec in selected_recipes_qs:
#             for ri in rec.recipe_ingredient.all():
#                 ing = ri.ingredient
#                 base_unit = ing.default_unit
#
#                 if ing.id not in needed:
#                     needed[ing.id] = {
#                         'ingredient': ing,
#                         'unit': base_unit,
#                         'total_qty': 0,
#                         'by_recipe': {},
#                     }
#
#                 try:
#                     converted_qty = convert_qty_to_unit(ri.quantity, ri.unit.unit, base_unit, ing)
#                     if converted_qty is None:
#                         messages.warning(request, f"Cannot convert {ri.unit.unit.code} for {ing.name}")
#                         converted_qty = ri.quantity
#                 except Exception:
#                     messages.warning(request, f"Cannot convert unit for {ing.name}")
#                     converted_qty = ri.quantity
#
#                 needed[ing.id]['total_qty'] += converted_qty
#                 needed[ing.id]['by_recipe'][rec] = needed[ing.id]['by_recipe'].get(rec, 0) + converted_qty
#
#         # Subtract what's already in the fridge, only add shortfall
#         fridge_items = UserFridge.objects.filter(user=user).select_related('ingredient', 'unit')
#
#         final_needed = {}
#         for ing_id, data in needed.items():
#             ing = data['ingredient']
#             needed_qty = data['total_qty']
#             base_unit = data['unit']  # this is a MeasurementUnit object
#
#             fridge_item = fridge_items.filter(ingredient=ing).first()
#             available_in_base = 0
#
#             if fridge_item:
#                 # Convert fridge quantity to base units using convert_qty_to_unit
#                 # which handles the same-unit case and uses IngredientMeasurementUnit lookups
#                 converted = convert_qty_to_unit(
#                     fridge_item.quantity,
#                     fridge_item.unit,   # MeasurementUnit
#                     base_unit,          # MeasurementUnit
#                     ing
#                 )
#                 if converted is not None:
#                     available_in_base = converted
#                 else:
#                     # Units are incompatible — warn but don't crash
#                     messages.warning(
#                         request,
#                         f"Could not convert fridge units for {ing.name} "
#                         f"({fridge_item.unit} → {base_unit}), ignoring fridge stock."
#                     )
#
#             shortfall = needed_qty - available_in_base
#             if shortfall > 0:
#                 final_needed[ing_id] = {
#                     'ingredient': ing,
#                     'quantity': round(shortfall, 4),
#                     'unit': base_unit,
#                     'by_recipe': data['by_recipe'],
#                 }
#
#         if not final_needed:
#             messages.info(request, "You already have all the ingredients in your fridge!")
#             return redirect('generate_grocery_list')
#
#         # ADD to existing grocery list quantities instead of overwriting
#         for ing_data in final_needed.values():
#             existing = UserGroceryList.objects.filter(
#                 user=user,
#                 ingredient=ing_data['ingredient'],
#                 unit=ing_data['unit']
#             ).first()
#
#             if existing:
#                 existing.quantity += ing_data['quantity']
#                 existing.save()
#             else:
#                 UserGroceryList.objects.create(
#                     user=user,
#                     ingredient=ing_data['ingredient'],
#                     quantity=ing_data['quantity'],
#                     unit=ing_data['unit']
#                 )
#
#         # Record a history entry for this generation
#         generation = GroceryListGeneration.objects.create(user=user)
#         for ing_data in final_needed.values():
#             for recipe_obj, qty in ing_data['by_recipe'].items():
#                 GroceryListGenerationItem.objects.create(
#                     generation=generation,
#                     recipe=recipe_obj,
#                     ingredient=ing_data['ingredient'],
#                     quantity=round(qty, 4),
#                     unit=ing_data['unit'],
#                 )
#
#         preview_items = list(final_needed.values())
#         preview_parts = [
#             f"{d['ingredient'].name} - {round(d['quantity'], 2)} {d['unit'].code if d['unit'] else ''}"
#             for d in preview_items[:3]
#         ]
#         remaining = len(preview_items) - 3
#         preview_str = ", ".join(preview_parts)
#         if remaining > 0:
#             preview_str += f" and {remaining} more"
#         preview_str += " added to your list!"
#
#         messages.success(request, preview_str)
#         return redirect('user_grocery_list')
#
#     return render(request, 'planner/generate_grocery_list.html', {
#         'page_obj': page_obj,
#         'recipes': page_obj.object_list,
#         'selected_recipes': selected_recipes,
#         'show_favs': show_favs,
#
#     })


# def user_grocery_list(request):
#     from collections import OrderedDict
#     user, _ = User.objects.get_or_create(username="default")
#     items = UserGroceryList.objects.filter(user=user).select_related('ingredient', 'unit')
#
#     raw_history = GroceryListGeneration.objects.filter(user=user).prefetch_related(
#         'items__ingredient',
#         'items__unit',
#         'items__recipe',
#     )
#
#     # Group items by recipe in Python so the template stays simple
#     history_data = []
#     for gen in raw_history:
#         by_recipe = OrderedDict()
#         for item in gen.items.all():
#             recipe_name = item.recipe.name if item.recipe else "Unknown Recipe"
#             if recipe_name not in by_recipe:
#                 by_recipe[recipe_name] = []
#             by_recipe[recipe_name].append(item)
#         history_data.append({
#             'created_at': gen.created_at,
#             'by_recipe': by_recipe,
#         })
#
#     history_paginator = Paginator(history_data, 5)
#     history_page_number = request.GET.get('history_page')
#     history_page_obj = history_paginator.get_page(history_page_number)
#
#     context = {
#         'items': items,
#         'history': history_page_obj,
#         'history_page_obj': history_page_obj,
#     }
#     return render(request, 'planner/user_grocery_list.html', context)


# def delete_grocery_item(request, item_id):
#     if request.method == "POST":
#         item = get_object_or_404(UserGroceryList, id=item_id)
#         item.delete()
#     return redirect("user_grocery_list")
#
#
# def add_grocery_to_fridge(request, item_id):
#     if request.method == "POST":
#         item = get_object_or_404(UserGroceryList, id=item_id)
#
#         UserFridge.objects.update_or_create(
#             user=item.user,
#             ingredient=item.ingredient,
#             defaults={
#                 "quantity": item.quantity,
#                 "unit": item.unit,
#             }
#         )
#         item.delete()
#
#     return redirect("user_grocery_list")
#
#
# def add_all_grocery_to_fridge(request):
#     if request.method == "POST":
#         user, _ = User.objects.get_or_create(username="default")
#         items = UserGroceryList.objects.filter(user=user)
#
#         for item in items:
#             UserFridge.objects.update_or_create(
#                 user=item.user,
#                 ingredient=item.ingredient,
#                 defaults={
#                     "quantity": item.quantity,
#                     "unit": item.unit,
#                 }
#             )
#         items.delete()
#
#     return redirect("user_grocery_list")


#
# def delete_grocery_item_by_id(request, id):
#     view = DeleteGroceryItemView.as_view()
#     return view(request, item_id=id)
