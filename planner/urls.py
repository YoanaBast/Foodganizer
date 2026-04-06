from django.urls import path, include

from planner import views
from planner.views import CalendarView, CalendarDataView, CalendarAddEntryView, CalendarEditEntryView, \
    CalendarDeleteEntryView, CalendarSearchView, CalendarDeficitView, MakeRecipeView, EmptyFridgeView

fridge_patterns = [
    # path('', views.manage_fridge, name='manage_fridge'),
    path('', views.ManageFridgeView.as_view(), name='manage_fridge'),

    # path('edit/<int:item_id>/', views.edit_fridge_item, name='edit_fridge_item'),
    path('edit/<int:item_id>/', views.EditFridgeItemView.as_view(), name='edit_fridge_item'),

    # path('add/', views.add_fridge_item, name='add_fridge_item'),
    path('add/', views.AddFridgeItemView.as_view(), name='add_fridge_item'),

    # path('<int:fridge_id>/delete/', views.delete_fridge_item, name='delete_fridge_item'),
    path('<int:fridge_id>/delete/', views.DeleteFridgeItemView.as_view(), name='delete_fridge_item'),
]

grocery_patterns = [
    # path('', views.user_grocery_list, name='user_grocery_list'),
    path('', views.UserGroceryListView.as_view(), name='user_grocery_list'),

    # path('generate/', views.generate_grocery_list, name='generate_grocery_list'),
    path('generate/', views.GenerateGroceryListView.as_view(), name='generate_grocery_list'),

    # path('delete/<int:item_id>/', views.delete_grocery_item, name='delete_grocery_item'),
    path('delete/<int:item_id>/', views.DeleteGroceryItemView.as_view(), name='delete_grocery_item'),


    # path('add-to-fridge/<int:item_id>/', views.add_grocery_to_fridge, name='add_grocery_to_fridge'),
    path('add-to-fridge/<int:item_id>/', views.AddGroceryToFridgeView.as_view(), name='add_grocery_to_fridge'),

    # path('add-all-to-fridge/', views.add_all_grocery_to_fridge, name='add_all_grocery_to_fridge'),
    path('add-all-to-fridge/', views.AddAllGroceryToFridgeView.as_view(), name='add_all_grocery_to_fridge'),
]

urlpatterns = [
    path('fridge/', include(fridge_patterns)),
    path('fridge/empty/', EmptyFridgeView.as_view(), name='empty_fridge'),

    path('grocery-list/', include(grocery_patterns)),
    path('calorie-tracker/', views.calorie_tracker, name='calorie-tracker'),
    path('suggestions/', views.get_meal_suggestions, name='meal_suggestions'),
    path('make/<int:id>/', MakeRecipeView.as_view(), name='make_recipe'),

    # path('meals/', views.meal_list, name='meal_list'),
    path('meals/', views.MealListView.as_view(), name='meal_list'),

    # urls.py
    path('fridge/anon/delete/<int:index>/', views.DeleteAnonFridgeItemView.as_view(), name='delete_anon_fridge_item'),
    path('fridge/anon/edit/<int:index>/', views.EditAnonFridgeItemView.as_view(), name='edit_anon_fridge_item'),
    path('grocery/anon/delete/<int:index>/', views.DeleteAnonGroceryItemView.as_view(), name='delete_anon_grocery_item'),
    path('grocery/anon/add-to-fridge/<int:index>/', views.AddAnonGroceryToFridgeView.as_view(), name='add_anon_grocery_to_fridge'),
    path('grocery/anon/add-all-to-fridge/', views.AddAllAnonGroceryToFridgeView.as_view(), name='add_all_anon_grocery_to_fridge'),
    path('biometrics/', views.BiometricsView.as_view(), name='biometrics'),
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('calendar/data/', CalendarDataView.as_view(), name='calendar_data'),
    path('calendar/add/', CalendarAddEntryView.as_view(), name='calendar_add'),
    path('calendar/edit/<int:entry_id>/', CalendarEditEntryView.as_view(), name='calendar_edit'),
    path('calendar/delete/<int:entry_id>/', CalendarDeleteEntryView.as_view(), name='calendar_delete'),
    path('calendar/search/', CalendarSearchView.as_view(), name='calendar_search'),
    path('calendar/deficit/', CalendarDeficitView.as_view(), name='calendar_deficit'),

]