"""Pure biometrics math. No DB, no session."""
from types import SimpleNamespace

from core.constants import ACTIVITY_MULTIPLIERS


def bmr(gender, weight_kg, height_cm, age):
    """Mifflin-St Jeor."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + 5, 2) if gender == 'M' else round(base - 161, 2)


def tdee(bmr_value, activity_level):
    return round(bmr_value * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2), 2)


def target_calories(tdee_value, deficit=0):
    return round(tdee_value + deficit, 2)


def summarize(data, deficit=0):
    """data: dict with gender, weight_kg, height_cm, age, activity_level."""
    b = bmr(data['gender'], data['weight_kg'], data['height_cm'], data['age'])
    t = tdee(b, data['activity_level'])
    from planner.services import nutrition_needs_core as nn
    target = target_calories(t, deficit)
    value = nn.bmi(data['weight_kg'], data['height_cm'])
    return SimpleNamespace(
        bmr=b, tdee=t, target_calories=target, updated_at=None,
        bmi=value, bmi_category=nn.bmi_category(value),
        nutrient_needs=nn.daily_needs(data['gender'], data['age'], data['weight_kg'], target),
    )
