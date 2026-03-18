from django.core.checks import messages

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


def build_needed_dict(selected_recipes_qs, request):
    needed = {}
    for rec in selected_recipes_qs:
        for ri in rec.recipe_ingredient.all():
            ing = ri.ingredient
            base_unit = ing.default_unit
            if ing.id not in needed:
                needed[ing.id] = {
                    'ingredient': ing,
                    'unit': base_unit,
                    'total_qty': 0,
                    'by_recipe': {},
                }
            try:
                converted_qty = convert_qty_to_unit(ri.quantity, ri.unit.unit, base_unit, ing)
                if converted_qty is None:
                    messages.warning(request, f"Cannot convert {ri.unit.unit.code} for {ing.name}")
                    converted_qty = ri.quantity
            except Exception:
                messages.warning(request, f"Cannot convert unit for {ing.name}")
                converted_qty = ri.quantity

            needed[ing.id]['total_qty'] += converted_qty
            needed[ing.id]['by_recipe'][rec] = needed[ing.id]['by_recipe'].get(rec, 0) + converted_qty
    return needed


def subtract_fridge(needed, fridge_items, request):
    final_needed = {}
    for ing_id, data in needed.items():
        ing = data['ingredient']
        base_unit = data['unit']
        fridge_item = fridge_items.filter(ingredient=ing).first()
        available_in_base = 0

        if fridge_item:
            converted = convert_qty_to_unit(fridge_item.quantity, fridge_item.unit, base_unit, ing)
            if converted is not None:
                available_in_base = converted
            else:
                messages.warning(request, f"Could not convert fridge units for {ing.name} ({fridge_item.unit} → {base_unit}), ignoring fridge stock.")

        shortfall = data['total_qty'] - available_in_base
        if shortfall > 0:
            final_needed[ing_id] = {
                'ingredient': ing,
                'quantity': round(shortfall, 4),
                'unit': base_unit,
                'by_recipe': data['by_recipe'],
            }
    return final_needed


def save_grocery_list(user, final_needed):
    for ing_data in final_needed.values():
        existing = UserGroceryList.objects.filter(
            user=user, ingredient=ing_data['ingredient'], unit=ing_data['unit']
        ).first()
        if existing:
            existing.quantity += ing_data['quantity']
            existing.save()
        else:
            UserGroceryList.objects.create(
                user=user,
                ingredient=ing_data['ingredient'],
                quantity=ing_data['quantity'],
                unit=ing_data['unit']
            )


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



def transfer_session_to_user(user, session):
    for item in session.pop('anon_fridge', []):
        UserFridge.objects.get_or_create(
            user=user,
            ingredient_id=item['ingredient_id'],
            unit_id=item['unit_id'],
            defaults={'quantity': item['quantity']}
        )

    for item in session.pop('anon_grocery', []):
        UserGroceryList.objects.get_or_create(
            user=user,
            ingredient_id=item['ingredient_id'],
            unit_id=item['unit_id'],
            defaults={'quantity': item['quantity']}
        )

    for item in session.pop('anon_meals', []):
        UserMealList.objects.create(
            user=user,
            recipe_id=item['recipe_id'],
        )

def get_user_fridge(request):
    """Returns DB queryset for authenticated users, session list for anon"""
    if request.user.is_authenticated:
        return UserFridge.objects.filter(user=request.user).select_related('ingredient__category', 'unit')
    return []  # session-based later, empty for now


def get_or_create_fridge_item(request, ingredient, qty, unit):
    """Add to DB fridge or session fridge depending on auth"""
    if request.user.is_authenticated:
        items = UserFridge.objects.filter(user=request.user, ingredient=ingredient)
        target_item = items.filter(unit=unit).first()
        if target_item:
            target_item.quantity += qty
            target_item.save()
        else:
            UserFridge.objects.create(user=request.user, ingredient=ingredient, quantity=qty, unit=unit)
    else:
        fridge = request.session.get('anon_fridge', [])
        for item in fridge:
            if item['ingredient_id'] == ingredient.id and item['unit_id'] == unit.id:
                item['quantity'] += qty
                request.session.modified = True
                return
        fridge.append({'ingredient_id': ingredient.id, 'unit_id': unit.id, 'quantity': qty})
        request.session['anon_fridge'] = fridge