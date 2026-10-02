from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.shortcuts import render
from django.views.generic import TemplateView


# Create your views here.!


class HomepageView(TemplateView):
    template_name = 'core/homepage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cards'] = [
            {"url_name": "generate_grocery_list", "title": "Get Grocery List",
             "description": "Save yourself the cognitive load and hours wondering in the store, generate a planner list from your favourite recipes!"},
            {"url_name": "user_grocery_list", "title": "My Grocery List",
             "description": "Check what you have in your planner list and start shopping! You can move items from this list to your fridge to keep track of your ingredients."},
            {"url_name": "biometrics", "title": "BMI + TDEE Calculator",
             "description": "BMR and TDEE calculator. Set your data and start tracking!"},
            {"url_name": "meal_suggestions", "title": "Get Meal Suggestions",
             "description": "See what you can cook right now with the ingredients in your fridge!"},
            {"url_name": "meal_list", "title": "My Meal Suggestions",
             "description": "A list of your generated meal suggestions. Just open it and start cooking!"},
            {"url_name": "calorie-tracker", "title": "KCALendar",
             "description": "Track your meals and nutrients in the calendar! See detailed information about your progress."},
            {"url_name": "manage_recipes", "title": "Global Recipes",
             "description": "Check out our recipes and add your own!"},
            {"url_name": "manage_ingredients", "title": "Global Ingredients",
             "description": "Browse ingredients, or introduce the Foodganizer to new flavours!"},
            {"url_name": "manage_fridge", "title": "My Fridge",
             "description": "Keep your digital fridge up to date with your real one here! You can generate recipe suggestions based on your available ingredients."},
        ]
        return context


def handler405(request, exception=None):
    """django does not have a 405 handler by default"""
    return render(request, '405.html', status=405)

