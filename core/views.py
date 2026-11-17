from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.shortcuts import render
from django.views.generic import TemplateView


# Create your views here.!


class HomepageView(TemplateView):
    template_name = 'core/homepage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cards'] = [
            {"url_name": "generate_grocery_list", "title": "Make Grocery List",
             "description": "Save yourself the cognitive load and hours wondering in the store, generate a planner list from your favourite recipes!"},

            {"url_name": "meal_suggestions", "title": "Fridge Meal Ideas",
             "description": "See what you can cook right now with the ingredients in your fridge!"},
            {"url_name": "calorie-tracker", "title": "KCALendar",
             "description": "Track your meals and nutrients in the calendar! See detailed information about your progress."},
            {"url_name": "manage_recipes", "title": "Recipes",
             "description": "Check out our recipes and add your own!"},
            {"url_name": "manage_ingredients", "title": "Ingredients",
             "description": "Browse ingredients, or introduce the Foodganizer to new flavours!"},
            {"url_name": "biometrics", "title": "BMI + TDEE Calculator",
             "description": "BMR and TDEE calculator. Set your data and start tracking!"},

                   ]
        return context


def handler405(request, exception=None):
    """django does not have a 405 handler by default"""
    return render(request, '405.html', status=405)

