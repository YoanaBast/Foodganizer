Welcome to my to-do list! Feel free to give me siggestions :)

# TO-DO

## PRIORITY 1 FIXES



## PRIORITY 2 FIXES
    - finish manual QA on API


## PRIORITY MEH FIXES
    - {{ item.unit }} for anon in the fridge, can it get the name for property recreated
    - change <br> to margin - did it for the most part but check again


## FEATURES
    - add more dummy data


## TEST


## UI
    - + button on categories, tags and unit is not obvious, maybe add a label
    - default should not be 0.01 for quantity, more work if the user chooses to use the arrows 
    
## EXTRA FEATURES
    - make a guide
    - make day/night widget
    - Meal suggestion - how many times I can prepare it 
    - Filter by days in my meal history, calendar 


## Notes:
1. This project was developed in 2 parts for an uni exam. The first one required no user auth. Now that I have an existing DB structure with multiple migrations, I will use a Profile model (OneToOne), as opposed to an AbstractUser class, because I'd like to keep my migrations - they mark my progress, my previous errors and redesigns I've done. 
2. The project uses WhiteNoise to serve static files because DEBUG=False. Without it, collectstatic doesn’t serve files correctly. DEBUG=False is required for the custom 404 page.




