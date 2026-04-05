from django.urls import path, include
from . import views

ajax_category_patterns = [
    path('', views.ListCategoriesAjaxView.as_view(), name='list_categories_ajax'),
    path('add/', views.AddCategoryAjaxView.as_view(), name='add_category_ajax'),
    path('<int:pk>/edit/', views.EditCategoryAjaxView.as_view(), name='edit_category_ajax'),
    path('<int:pk>/delete/', views.DeleteCategoryAjaxView.as_view(), name='delete_category_ajax'),
]

ajax_dietary_tag_patterns = [
    path('', views.ListDietaryTagsAjaxView.as_view(), name='list_dietary_tags_ajax'),
    path('add/', views.AddDietaryTagAjaxView.as_view(), name='add_dietary_tag_ajax'),
    path('fragment/', views.DietaryTagsFragmentView.as_view(), name='dietary_tags_fragment'),
    path('<int:pk>/edit/', views.EditDietaryTagAjaxView.as_view(), name='edit_dietary_tag_ajax'),
    path('<int:pk>/delete/', views.DeleteDietaryTagAjaxView.as_view(), name='delete_dietary_tag_ajax'),
]

ajax_unit_patterns = [
    path('add/', views.AddMeasurementUnitAjaxView.as_view(), name='add_measurement_unit_ajax'),
    path('', views.ListMeasurementUnitsAjaxView.as_view(), name='list_measurement_units_ajax'),
    path('<int:pk>/edit/', views.EditMeasurementUnitAjaxView.as_view(), name='edit_measurement_unit_ajax'),
    path('<int:pk>/delete/', views.DeleteMeasurementUnitAjaxView.as_view(), name='delete_measurement_unit_ajax'),
]

ajax_patterns = [
    path('category/', include(ajax_category_patterns)),
    path('dietary-tag/', include(ajax_dietary_tag_patterns)),
    path('unit/', include(ajax_unit_patterns)),
]

ingredient_unit_patterns = [
    path('add/', views.AddMeasurementUnitView.as_view(), name='add_measurement_unit'),
    path('<int:imu_id>/delete/', views.DeleteMeasurementUnitView.as_view(), name='delete_measurement_unit'),
]

ingredient_detail_patterns = [
    path('', views.IngredientDetailView.as_view(), name='ingredient_detail'),
    path('edit/', views.EditIngredientView.as_view(), name='edit_ingredient'),
    path('delete/', views.DeleteIngredientView.as_view(), name='delete_ingredient'),
    path('unit/', include(ingredient_unit_patterns)),
    path('units/<int:imu_id>/edit/', views.EditMeasurementUnitConversionView.as_view(), name='edit_measurement_unit_conversion'),
]

urlpatterns = [
    path('', views.ManageIngredientsView.as_view(), name='manage_ingredients'),
    path('add/', views.AddIngredientView.as_view(), name='add_ingredient'),
    path('<int:ingredient_id>/', include(ingredient_detail_patterns)),
    path('ajax/', include(ajax_patterns)),
]