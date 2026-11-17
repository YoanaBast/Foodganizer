from django import template

from planner.services.nutrition_needs_core import needs_rows

register = template.Library()


@register.inclusion_tag('planner/_nutrient_needs.html')
def nutrient_needs(user):
    """BMI + daily nutrient needs for a user; shows a prompt if they have no biometrics."""
    bio = getattr(user, 'biometrics', None)  # RelatedObjectDoesNotExist is an AttributeError
    return {
        'bio': bio,
        'rows': needs_rows(bio.nutrient_needs) if bio else [],
    }
