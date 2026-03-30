Welcome to my to-do list! Feel free to give me siggestions :)

# TO-DO
## PRIORITY 1 FIXES
    - test pagination w search
    - When DEBUG=True, Django serves media files itself via django.views.static.serve. When DEBUG=False, it stops doing that — you're supposed to have a real server (nginx, etc.) handle it.
    - check favourites table 
    - 429.html 
    - fix allowed hosts
    - change django secure key
    - hide allowed hosts, email from
    - manage.py check --deploy
    - s3 or something for media?

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






Critical

Set DEBUG=False in your .env
Make sure SECRET_KEY is a strong random key, not the default
Add your actual domain to ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
Switch SECURE_PROXY_SSL_HEADER value from http to https

Important

Add the named volume for the DB (as discussed earlier) so data persists
Make sure your .env is in .gitignore — never commit it
Set up SSL/HTTPS on your server (usually via Certbot + Nginx)

Nice to have

Add a health check to your db service so the web container waits for Postgres to be actually ready (not just started):







