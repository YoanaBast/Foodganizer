[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Ultra&size=29&pause=1000&color=0CF724&width=435&lines=Foodganizer)](https://git.io/typing-svg)

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Teko&size=25&pause=1000&color=432FF7&width=435&lines=Python+%7C+Django+%7C+HTML+%7C+CSS+%7C+JS+%7C+PostgreSQL)](https://git.io/typing-svg)

The Foodganizer is built around one idea: you're in control. Every recipe, ingredient, unit, category, and tag is yours to create and customise. Fill your digital fridge and get meal suggestions that won't send you to the store! Or if you feel like going out, geenrate a grocery list fast and easy from recipes of your choice! 

If you hate the cognitive load that comes with planning meals every single day - this app is for you!

## Project Structure
[Project Structure](docs/project_structure.md)

## Installation
[Local Installation](docs/local_install.md)

## Notes:
1. This project was developed in 2 parts for an uni exam. The first one required no user auth. Now that I have an existing DB structure with multiple migrations, I will use a Profile model (OneToOne), as opposed to an AbstractUser class, because I'd like to keep my migrations - they mark my progress, my previous errors and redesigns I've done. 
2. The project uses WhiteNoise to serve static files because DEBUG=False. Without it, collectstatic doesn’t serve files correctly. DEBUG=False is required for the custom 404 page.

## See Also:
- [AI & Tools Used](docs/ai_tools.md)
- [What I've Learned](docs/what_ive_learned.md)
- [TO-DO List](docs/to_do.md)

