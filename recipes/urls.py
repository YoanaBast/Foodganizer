from django.urls import path, include
from . import views


recipe_detail_patterns = [
    path('<int:pk>/', views.RecipeDetailView.as_view(), name='recipe_detail'),
    path('<int:pk>/edit/', views.EditRecipeView.as_view(), name='edit_recipe'),
    path('<int:pk>/delete/', views.DeleteRecipeView.as_view(), name='delete_recipe'),
    path('<int:pk>/add_ingredient/', views.AddIngredientToRecipeView.as_view(), name='add_ingredient'),
    path('<int:pk>/toggle_fav/', views.ToggleFavouriteView.as_view(), name='toggle_favourite'),
]

recipe_category_patterns = [
    path('add/', views.AddRecipeCategoryAjaxView.as_view(), name='add_recipe_category_ajax'),
    path('list/', views.ListRecipeCategoriesAjaxView.as_view(), name='list_recipe_categories_ajax'),
    path('<int:pk>/edit/', views.EditRecipeCategoryAjaxView.as_view(), name='edit_recipe_category_ajax'),
    path('<int:pk>/delete/', views.DeleteRecipeCategoryAjaxView.as_view(), name='delete_recipe_category_ajax'),
]

urlpatterns = [
    path('', views.ManageRecipesView.as_view(), name='manage_recipes'),
    path('add/', views.AddRecipeView.as_view(), name='add_recipe'),
    path('ajax/recipe-categories/', include(recipe_category_patterns)),
    path('', include(recipe_detail_patterns)),
]