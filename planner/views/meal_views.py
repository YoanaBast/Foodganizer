from django.db.models import Prefetch
from django.utils import timezone
from django.views import View

from planner.helpers import check_anon_fridge_for_recipe, subtract_anon_fridge_for_recipe, subtract_fridge_for_recipe, \
    check_fridge_for_recipe
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
        fridge_items = list(
            UserFridge.objects
            .filter(user=request.user)
            .select_related('ingredient', 'unit')
        )
        use_session = False
    else:
        fridge_items = request.session.get('anon_fridge', [])
        use_session = True

    recipes = Recipe.objects.prefetch_related(
        Prefetch(
            'recipe_ingredient',
            queryset=RecipeIngredient.objects.select_related(
                'ingredient',
                'unit__unit',
            )
        )
    )

    # Load all IngredientMeasurementUnit conversions needed by the
    # anonymous fridge in ONE query.
    if use_session:
        fridge_unit_ids = {
            item['unit_id']
            for item in fridge_items
            if item.get('unit_id')
        }

        conversions = IngredientMeasurementUnit.objects.filter(
            unit_id__in=fridge_unit_ids
        )

        conversion_map = {
            (conversion.ingredient_id, conversion.unit_id): conversion.conversion_to_base
            for conversion in conversions
        }

        unit_map = {
            unit.id: unit
            for unit in MeasurementUnit.objects.filter(id__in=fridge_unit_ids)
        }

    suggestions = []

    for recipe in recipes:
        recipe_ingredients = recipe.recipe_ingredient.all()
        total = len(recipe_ingredients)
        matched = 0
        missing = []

        for ri in recipe_ingredients:
            fridge_qty = 0

            if use_session:
                for fridge_item in fridge_items:
                    if fridge_item['ingredient_id'] != ri.ingredient_id:
                        continue

                    fridge_unit = unit_map.get(fridge_item.get('unit_id'))

                    if not fridge_unit:
                        continue

                    if ri.unit and fridge_unit.id == ri.unit.unit_id:
                        fridge_qty = fridge_item['quantity']
                    else:
                        conversion = conversion_map.get(
                            (ri.ingredient_id, fridge_unit.id)
                        )

                        if conversion and ri.unit:
                            qty_in_base = (
                                fridge_item['quantity'] * conversion
                            )
                            fridge_qty = (
                                qty_in_base / ri.unit.conversion_to_base
                            )

                    break

            else:
                fridge_item = next(
                    (
                        f for f in fridge_items
                        if f.ingredient_id == ri.ingredient_id
                    ),
                    None
                )

                if fridge_item:
                    if fridge_item.unit == ri.unit.unit:
                        fridge_qty = fridge_item.quantity
                    else:
                        conversion = IngredientMeasurementUnit.objects.filter(
                            ingredient=ri.ingredient,
                            unit=fridge_item.unit,
                        ).first()

                        if conversion:
                            qty_in_base = (
                                fridge_item.quantity
                                * conversion.conversion_to_base
                            )
                            fridge_qty = (
                                qty_in_base / ri.unit.conversion_to_base
                            )

            if fridge_qty >= ri.quantity:
                matched += 1
            else:
                missing_qty = round(
                    max(ri.quantity - fridge_qty, 0),
                    2
                )
                unit_code = (
                    ri.unit.unit.code
                    if ri.unit and ri.unit.unit
                    else ""
                )
                missing.append(
                    f"{missing_qty:g}{unit_code} {ri.ingredient.name}"
                )

        match_percent = int((matched / total) * 100) if total else 0

        suggestions.append({
            "recipe": recipe,
            "match_percent": match_percent,
            "can_make": matched == total and total > 0,
            "missing_ingredients": missing,
        })

    suggestions.sort(
        key=lambda x: x["match_percent"],
        reverse=True
    )

    paginator = Paginator(suggestions, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        "planner/meals/get_meal_suggestions.html",
        {
            "suggestions": page_obj,
            "page_obj": page_obj,
        }
    )


"""
MEALS/RECIPES MADE VIEWS 
"""


class MakeRecipeView(View):
    def post(self, request, id):
        recipe = get_object_or_404(
            Recipe.objects.prefetch_related(
                Prefetch('recipe_ingredient',
                    queryset=RecipeIngredient.objects.select_related('ingredient', 'unit__unit'))
            ), id=id
        )

        if request.user.is_authenticated:
            return self._handle_auth(request, recipe)
        return self._handle_anon(request, recipe)

    def _handle_auth(self, request, recipe):
        fridge_items = UserFridge.objects.filter(user=request.user)

        missing = check_fridge_for_recipe(recipe, fridge_items)
        if missing:
            messages.error(request, f"Not enough ingredients: {missing}")
            return redirect('meal_suggestions')

        subtract_fridge_for_recipe(recipe, fridge_items)

        UserMealList.objects.create(user=request.user, recipe=recipe)
        CalendarEntry.objects.create(
            user=request.user,
            date=timezone.now().date(),
            recipe=recipe,
            servings=recipe.servings,
            source='meal_suggestion',
        )
        messages.success(request, (
            f'<b>{recipe.name.title()}</b> made successfully! '
            # f'<a href="{reverse("recipe_detail", kwargs={"pk": recipe.id})}">View recipe</a> · '
            # f'<a href="{reverse("meal_list")}">Meal history</a> · '
            # f'<a href="{reverse("manage_fridge")}">Check your fridge</a>'
        ))
        return redirect('meal_suggestions')

    def _handle_anon(self, request, recipe):
        anon_fridge = request.session.get('anon_fridge', [])

        missing = check_anon_fridge_for_recipe(recipe, anon_fridge)
        if missing:
            messages.error(request, f"Not enough ingredients: {missing}")
            return redirect('meal_suggestions')

        subtract_anon_fridge_for_recipe(recipe, request)

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


class MealListView(ListView):
    template_name = 'planner/meals/meal_list.html'
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

