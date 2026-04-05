# helpers.py
from django.contrib import messages
from planner.helpers import convert_qty_to_unit
from planner.models import UserGroceryList


def build_needed_dict(selected_recipes_qs, request):
    needed = {}
    for rec in selected_recipes_qs:
        for ri in rec.recipe_ingredient.all():
            ing = ri.ingredient
            ri_imu = ri.unit                  # IngredientMeasurementUnit
            ri_unit = ri_imu.unit             # MeasurementUnit
            base_unit = ing.default_unit      # MeasurementUnit or None

            if ing.id not in needed:
                needed[ing.id] = {
                    'ingredient': ing,
                    'unit': base_unit or ri_unit,  # fallback to recipe unit if no default
                    'total_qty': 0,
                    'by_recipe': {},
                }

            effective_base = needed[ing.id]['unit']

            if ri_unit != effective_base:
                converted_qty = convert_qty_to_unit(ri.quantity, ri_unit, effective_base, ing)
                if converted_qty is None:
                    messages.warning(request, f"Cannot convert {ri_unit} → {effective_base} for {ing.name}.")
                    converted_qty = ri.quantity
            else:
                converted_qty = ri.quantity

            needed[ing.id]['total_qty'] += converted_qty
            needed[ing.id]['by_recipe'][rec] = needed[ing.id]['by_recipe'].get(rec, 0) + converted_qty

    return needed


def save_grocery_list(user, final_needed):
    for ing_data in final_needed.values():
        # Match on ingredient only — one entry per ingredient per user
        existing = UserGroceryList.objects.filter(
            user=user,
            ingredient=ing_data['ingredient'],
        ).first()
        if existing:
            existing.quantity += ing_data['quantity']
            existing.save()
        else:
            UserGroceryList.objects.create(
                user=user,
                ingredient=ing_data['ingredient'],
                quantity=ing_data['quantity'],
                unit=ing_data['unit'],
            )