from django.utils import timezone
from planner.models import CalendarEntry
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit

from planner.models import UserFridge, UserGroceryList, GroceryListGeneration, GroceryListGenerationItem, UserMealList
from recipes.models import Recipe, RecipeIngredient


def get_meal_suggestions(request):
    if request.user.is_authenticated:
        fridge_items = list(UserFridge.objects.filter(user=request.user).select_related('ingredient', 'unit'))
        use_session = False
    else:
        fridge_items = request.session.get('anon_fridge', [])
        use_session = True

    recipes = Recipe.objects.all()
    suggestions = []

    for recipe in recipes:
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        total = recipe_ingredients.count()
        matched = 0
        missing = []

        for ri in recipe_ingredients:
            fridge_qty = 0

            if use_session:
                for fridge_item in fridge_items:
                    if fridge_item['ingredient_id'] != ri.ingredient.id:
                        continue
                    try:
                        fridge_unit = MeasurementUnit.objects.get(id=fridge_item['unit_id'])
                        if fridge_unit == ri.unit.unit:
                            fridge_qty = fridge_item['quantity']
                        else:
                            conv_fridge = IngredientMeasurementUnit.objects.get(
                                ingredient=ri.ingredient, unit=fridge_unit
                            )
                            qty_in_base = fridge_item['quantity'] * conv_fridge.conversion_to_base
                            fridge_qty = qty_in_base / ri.unit.conversion_to_base
                    except (MeasurementUnit.DoesNotExist, IngredientMeasurementUnit.DoesNotExist):
                        fridge_qty = 0
            else:
                fridge_item = next((f for f in fridge_items if f.ingredient == ri.ingredient), None)
                if fridge_item:
                    if fridge_item.unit == ri.unit.unit:
                        fridge_qty = fridge_item.quantity
                    else:
                        try:
                            conv_fridge = IngredientMeasurementUnit.objects.get(
                                ingredient=ri.ingredient, unit=fridge_item.unit
                            )
                            qty_in_base = fridge_item.quantity * conv_fridge.conversion_to_base
                            fridge_qty = qty_in_base / ri.unit.conversion_to_base
                        except IngredientMeasurementUnit.DoesNotExist:
                            fridge_qty = 0

            if fridge_qty >= ri.quantity:
                matched += 1
            else:
                missing_qty = round(max(ri.quantity - fridge_qty, 0), 2)
                missing.append(f"{missing_qty:g}{ri.unit.unit.code} {ri.ingredient.name}")

        match_percent = int((matched / total) * 100) if total else 0
        suggestions.append({
            "recipe": recipe,
            "match_percent": match_percent,
            "can_make": matched == total and total > 0,
            "missing_ingredients": missing
        })

    suggestions.sort(key=lambda x: x["match_percent"], reverse=True)
    paginator = Paginator(suggestions, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "planner/get_meal_suggestions.html", {
        "suggestions": page_obj,
        "page_obj": page_obj,
    })


"""
MEALS/RECIPES MADE VIEWS 
"""


def make_recipe(request, id):
    if request.method != 'POST':
        return redirect('meal_suggestions')

    recipe = get_object_or_404(Recipe, id=id)

    if not request.user.is_authenticated:
        anon_fridge = request.session.get('anon_fridge', [])

        # check ingredients
        for ri in recipe.recipe_ingredient.all():
            fridge_qty = 0
            for item in anon_fridge:
                if item['ingredient_id'] != ri.ingredient.id:
                    continue
                try:
                    fridge_unit = MeasurementUnit.objects.get(id=item['unit_id'])
                    conv = IngredientMeasurementUnit.objects.get(ingredient=ri.ingredient, unit=fridge_unit)
                    fridge_qty = (item['quantity'] * conv.conversion_to_base) / ri.unit.conversion_to_base
                except (MeasurementUnit.DoesNotExist, IngredientMeasurementUnit.DoesNotExist):
                    fridge_qty = 0

            if fridge_qty < ri.quantity:
                messages.error(request, f"Not enough ingredients: {ri.ingredient.name}")
                return redirect('meal_suggestions')

        # subtract from session fridge
        new_fridge = []
        recipe_ingredients = {ri.ingredient.id: ri for ri in recipe.recipe_ingredient.all()}

        for item in anon_fridge:
            ri = recipe_ingredients.get(item['ingredient_id'])
            if not ri:
                new_fridge.append(item)
                continue
            try:
                fridge_unit = MeasurementUnit.objects.get(id=item['unit_id'])
                conv = IngredientMeasurementUnit.objects.get(ingredient=ri.ingredient, unit=fridge_unit)
                qty_to_subtract = (ri.quantity * ri.unit.conversion_to_base) / conv.conversion_to_base
                remaining = item['quantity'] - qty_to_subtract
                if remaining > 0:
                    new_fridge.append({**item, 'quantity': remaining})
            except (MeasurementUnit.DoesNotExist, IngredientMeasurementUnit.DoesNotExist):
                new_fridge.append(item)

        request.session['anon_fridge'] = new_fridge

        # save to session meals
        anon_meals = request.session.get('anon_meals', [])
        anon_meals.append({
            'recipe_id': recipe.id,
            'recipe_name': recipe.name,
            'made_at': timezone.now().isoformat(),
        })
        request.session['anon_meals'] = anon_meals
        request.session.modified = True

        messages.success(request, f'<b>{recipe.name.title()}</b> made successfully!')
        return redirect('meal_suggestions')


    fridge_items = UserFridge.objects.filter(user=request.user)

    for ri in recipe.recipe_ingredient.all():
        fridge_item = fridge_items.filter(ingredient=ri.ingredient).first()
        available_qty = 0

        if fridge_item:
            try:
                fridge_unit_obj = IngredientMeasurementUnit.objects.get(
                    ingredient=ri.ingredient, unit=fridge_item.unit
                )
                available_qty = (fridge_item.quantity * fridge_unit_obj.conversion_to_base) / ri.unit.conversion_to_base
            except IngredientMeasurementUnit.DoesNotExist:
                available_qty = 0


        if available_qty < ri.quantity:
            messages.error(request, f"Not enough ingredients: {ri.ingredient.name}")
            return redirect('meal_suggestions')

    UserMealList.objects.create(user=request.user, recipe=recipe)
    messages.success(request, (
        f'<b>{recipe.name.title()}</b> made successfully! '
        f'<a href="{reverse("recipe_detail", kwargs={"pk": recipe.id})}">View recipe</a> · '
        f'<a href="{reverse("meal_list")}">Meal history</a> · '
        f'<a href="{reverse("manage_fridge")}">Check your fridge</a>'
    ))

    CalendarEntry.objects.create(
        user=request.user,
        date=timezone.now().date(),
        recipe=recipe,
        servings=recipe.servings,
        source='meal_suggestion',
    )
    return redirect('meal_suggestions')


class MealListView(ListView):
    template_name = 'planner/meal_list.html'
    context_object_name = 'meals'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserMealList.objects.filter(user=self.request.user).select_related('recipe')
        return UserMealList.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            anon_meals = self.request.session.get('anon_meals', [])
            resolved = []
            for item in anon_meals:
                try:
                    resolved.append({
                        'recipe': Recipe.objects.get(id=item['recipe_id']),
                        'made_at': item['made_at'],
                    })
                except Recipe.DoesNotExist:
                    resolved.append({
                        'recipe': None,
                        'made_at': item['made_at'],
                    })
            context['anon_meals'] = resolved
        return context

