from django.contrib import admin

from planner.models import UserFridge, UserBiometrics, CalendarEntry

# Register your models here.

# planner/admin.py
from django.contrib import admin
from .models import UserFridge, UserGroceryList, GroceryListGeneration, GroceryListGenerationItem, UserMealList



@admin.register(UserFridge)
class UserFridgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ingredient', 'quantity', 'unit')
    list_filter = ('user', 'unit')
    search_fields = ('user__username', 'ingredient__name')


@admin.register(UserGroceryList)
class UserGroceryListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ingredient', 'quantity', 'unit')
    list_filter = ('user', 'unit')
    search_fields = ('user__username', 'ingredient__name')


@admin.register(GroceryListGeneration)
class GroceryListGenerationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username',)


@admin.register(GroceryListGenerationItem)
class GroceryListGenerationItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'generation', 'recipe', 'ingredient', 'quantity', 'unit')
    list_filter = ('unit',)
    search_fields = ('ingredient__name', 'recipe__name')


@admin.register(UserMealList)
class UserMealListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'made_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')


@admin.register(UserBiometrics)
class UserBiometricsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'gender', 'age', 'weight_kg', 'height_cm', 'activity_level', 'unit_system', 'deficit_target', 'updated_at')
    list_filter = ('gender', 'activity_level', 'unit_system', 'deficit_target')
    search_fields = ('user__username',)

@admin.register(CalendarEntry)
class CalendarEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'recipe', 'ingredient', 'source')
    list_filter = ('source', 'user')
    search_fields = ('user__username',)