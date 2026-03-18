from django.contrib import admin
from django.utils.html import mark_safe

from django import forms

from .forms import RecipeFormAdmin
# Register your models here.
from .models import Recipe, RecipeIngredient, RecipeCategory



@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeFormAdmin

    list_display = (
        'id',
        'name',
        'category',
        'cooking_duration',
        'servings',
        'display_ingredients',
        'instructions',
        'display_favourites',
        'created_by',
        'updated_by',
        'created_at',
        'updated_at',
        'display_nutrients',

    )
    search_fields = ('name',)

    def display_ingredients(self, obj):
        return ", ".join([ri.ingredient.name for ri in obj.recipe_ingredient.all()])
    display_ingredients.short_description = "Ingredients"

    def display_nutrients(self, obj):
        nutrients = obj.nutrients
        return mark_safe("<br>".join(f"{k.capitalize()}: {v}" for k, v in nutrients.items()))
    display_nutrients.short_description = "Nutrients"

    def display_favourites(self, obj):
        return ", ".join([user.username for user in obj.favourited_by.all()]) or "-"
    display_favourites.short_description = "Favourited By"


@admin.register(RecipeCategory)
class RecipeCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_by', 'updated_by', 'created_at', 'updated_at')
    search_fields = ('name',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'quantity', 'unit')
    list_filter = ('unit',)
