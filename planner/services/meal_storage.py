from abc import ABC, abstractmethod

from django.utils import timezone

from planner.models import UserMealList

SESSION_KEY = 'anon_meals'


class MealStorage(ABC):
    @abstractmethod
    def record(self, recipe):
        """Log that the recipe was made."""


class DbMeals(MealStorage):
    def __init__(self, user):
        self.user = user

    def record(self, recipe):
        UserMealList.objects.create(user=self.user, recipe=recipe)


class SessionMeals(MealStorage):
    def __init__(self, session):
        self.session = session

    def record(self, recipe):
        meals = self.session.get(SESSION_KEY, [])
        meals.append({
            'recipe_id': recipe.id,
            'recipe_name': recipe.name,
            'made_at': timezone.now().isoformat(),
        })
        self.session[SESSION_KEY] = meals
        self.session.modified = True


def get_meals(request):
    if request.user.is_authenticated:
        return DbMeals(request.user)
    return SessionMeals(request.session)
