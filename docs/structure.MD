## where do hardcoded values live (ex. nutrient names, gender options)
- core/constraints.py

## where do sercrets live
- .env

## App responsibility
- core -> homepage, mixins
- ingredients -> ingredients and related models, CRUD admin site for ingredients
- recipes -> recipes and related models, CRUS, admin 
- meals_manager -> project settings
- planner:
  - grocery -> a grocery list generator based on targeted recies
  - fridge -> a digital fridge where users can hold ingredients, can import from grocery list
  - meals -> get meal suggestions based on what is in the fridge, keep meal history
  - KCAlendar -> tracks consumed meals against user target
  - biometrics - links to user, kcal targets
- Users -> extends django user with profile picture, bio, and historical records. Connects to the biometrics