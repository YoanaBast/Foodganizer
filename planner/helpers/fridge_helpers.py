from django.contrib import messages
from ingredients.models import IngredientMeasurementUnit, Ingredient, MeasurementUnit
from planner.models import GroceryListGeneration, GroceryListGenerationItem, UserGroceryList, UserFridge, UserMealList


def convert_qty_to_unit(qty, from_unit, to_unit, ingredient):
    """
    Convert qty of ingredient FROM from_unit TO to_unit using IngredientMeasurementUnit.
    Returns converted quantity or None if conversion not possible.
    """
    if from_unit == to_unit:
        return qty
    try:
        from_conv = IngredientMeasurementUnit.objects.get(ingredient=ingredient, unit=from_unit)
        to_conv = IngredientMeasurementUnit.objects.get(ingredient=ingredient, unit=to_unit)
        qty_in_base = qty * from_conv.conversion_to_base
        qty_in_target = qty_in_base / to_conv.conversion_to_base
        return qty_in_target
    except IngredientMeasurementUnit.DoesNotExist:
        return None








def save_generation_history(user, final_needed):
    generation = GroceryListGeneration.objects.create(user=user)
    for ing_data in final_needed.values():
        for recipe_obj, qty in ing_data['by_recipe'].items():
            GroceryListGenerationItem.objects.create(
                generation=generation,
                recipe=recipe_obj,
                ingredient=ing_data['ingredient'],
                quantity=round(qty, 4),
                unit=ing_data['unit'],
            )


"""
the functions below are used for storing anon user data when they decide they want to register, allowing them to transfer their fridge and other things and keep them in DB
"""


def build_preview_message(final_needed):
    preview_items = list(final_needed.values())
    preview_parts = [
        f"{d['ingredient'].name} - {round(d['quantity'], 2)} {d['unit'].code if d['unit'] else ''}"
        for d in preview_items[:3]
    ]
    remaining = len(preview_items) - 3
    preview_str = ", ".join(preview_parts)
    if remaining > 0:
        preview_str += f" and {remaining} more"
    return preview_str + " added to your list!"










