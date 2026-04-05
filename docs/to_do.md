Welcome to my to-do list! Feel free to give me siggestions :)

# TO-DO
## PRIORITY 1 FIXES
    - test pagination w search
    - 429.html 
    - fix dns for email replies
    - manage.py check --deploy
    - make sure to pip freeze befoe the 7th
     - verify all custom errs - 404 yes on dev
    - finish manual QA on API

## PRIORITY 2 FIXES
    - {{ item.unit }} for anon in the fridge, can it get the name for property recreated
    - change <br> to margin 
    - confuigure security in AWS to allow only cloudflare

## FEATURES
    - add more dummy data
    - add select boxes and select all with option to delete all ? bulk actions


## TEST

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


## Notes:
1. This project was developed in 2 parts for an uni exam. The first one required no user auth. Now that I have an existing DB structure with multiple migrations, I will use a Profile model (OneToOne), as opposed to an AbstractUser class, because I'd like to keep my migrations - they mark my progress, my previous errors and redesigns I've done. 
2. The project uses WhiteNoise to serve static files because DEBUG=False. Without it, collectstatic doesn’t serve files correctly. DEBUG=False is required for the custom 404 page.




