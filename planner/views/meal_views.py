from planner.services.meal_storage import get_meals
from planner.services.fridge_storage import get_fridge
from django.db.models import Prefetch
from django.utils import timezone
from django.views import View

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
    recipes = Recipe.objects.prefetch_related(
        Prefetch(
            'recipe_ingredient',
            queryset=RecipeIngredient.objects.select_related('ingredient', 'unit__unit'),
        )
    )
    suggestions = get_fridge(request).recipe_matches(recipes)
    page_obj = Paginator(suggestions, 10).get_page(request.GET.get('page'))
    return render(request, "planner/meals/get_meal_suggestions.html", {
        "suggestions": page_obj,
        "page_obj": page_obj,
    })


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
        missing = get_fridge(request).first_missing_for_recipe(recipe)
        if missing:
            messages.error(request, f"Not enough ingredients: {missing}")
            return redirect('meal_suggestions')

        get_fridge(request).consume_recipe(recipe)

        get_meals(request).record(recipe)
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
        missing = get_fridge(request).first_missing_for_recipe(recipe)
        if missing:
            messages.error(request, f"Not enough ingredients: {missing}")
            return redirect('meal_suggestions')

        get_fridge(request).consume_recipe(recipe)

        get_meals(request).record(recipe)

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

