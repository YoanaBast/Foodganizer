from django.urls import path
from . import views

urlpatterns = [
    # Ingredients
    path('ingredients/', views.ListCreateIngredientApiView.as_view(), name='api_ingredients_list_create'),
    path('ingredients/<int:pk>/', views.RetrieveUpdateDestroyIngredientApiView.as_view(), name='api_ingredients_detail'),
    path('ingredients/<int:pk>/units/', views.AddIngredientMeasurementUnitApiView.as_view(), name='api_ingredients_add_unit'),

    # Recipes
    path('recipes/', views.ListCreateRecipeApiView.as_view(), name='api_recipes_list_create'),
    path('recipes/<int:pk>/', views.RetrieveUpdateDestroyRecipeApiView.as_view(), name='api_recipes_detail'),
]