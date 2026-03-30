Welcome to my to-do list! Feel free to give me siggestions :)

# TO-DO
## PRIORITY 1 FIXES
    - test pagination w search
    - When DEBUG=True, Django serves media files itself via django.views.static.serve. When DEBUG=False, it stops doing that — you're supposed to have a real server (nginx, etc.) handle it.
    - check favourites table 
    - 429.html 

## PRIORITY 2 FIXES
    - Generation History needs to show what was added too
    - {{ item.unit }} for anon in the fridge, can it get the name for property recreated
    - hide the bubble menu on mobile or move it somewhere
    - tests
    - change <br> to margin 
    - add a better rash can in the category/tag menu

## FEATURES
    - add more dummy data
    - add select boxes and select all with option to delete all ? bulk actions
    - add count of favoutited by and sort by popularity for recipes
    - add sort by kcal, filter by tags/category
    - rara: Real deficit of 2914.6 kcal. That is 37.2% from 1kg of fat lost in 31 days. add also how many kg for bigger nums


## TEST
    - math 

## UI
    - + button on categories, tags and unit is not obvious, maybe add a label
    - default should not be 0.01 for quantity, more work if the user chooses to use the arrows 
    
## EXTRA FEATURES
    - make a guide
    - make day/night widget
    - have a check that allows edit/delete only on fields created by a specific user (user cannot delete public ingredients made by other users)
    - created by will be added to models once i implement auth
    - Meal suggestion - how many times I can prepare it 
    - Filter by days in my meal history, calendar 














