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
    """
    for the GenerateGroceryListView

    """
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




def get_user_fridge(request):
    """Returns DB queryset for authenticated users, session list for anon"""
    if request.user.is_authenticated:
        return UserFridge.objects.filter(user=request.user).select_related('ingredient__category', 'unit')
    return []  # session-based later, empty for now


def get_or_create_fridge_item(request, ingredient, qty, unit):
    """
    adds fridge item to user fridge or does the math to combine it if already exists
    """
    user = request.user
    items = UserFridge.objects.filter(user=user, ingredient=ingredient)
    target_item = items.filter(unit=unit).first()

    for item in items.exclude(id=getattr(target_item, "id", None)):
        try:
            item_unit_conv = IngredientMeasurementUnit.objects.get(ingredient=ingredient, unit=item.unit)
            target_unit_conv = IngredientMeasurementUnit.objects.get(ingredient=ingredient, unit=unit)
        except IngredientMeasurementUnit.DoesNotExist:
            continue

        qty_in_base = item.quantity * item_unit_conv.conversion_to_base
        qty_in_target = qty_in_base / target_unit_conv.conversion_to_base

        if target_item:
            target_item.quantity += qty_in_target
            target_item.save()
        else:
            target_item = UserFridge.objects.create(
                user=user, ingredient=ingredient,
                quantity=qty_in_target, unit=unit
            )
        item.delete()

    if target_item:
        target_item.quantity += qty
        target_item.save()
    else:
        UserFridge.objects.create(
            user=user, ingredient=ingredient,
            quantity=qty, unit=unit
        )


def get_or_create_anon_fridge_item(request, ingredient, qty, unit):
    fridge = request.session.get('anon_fridge', [])
    target_index = None
    target_unit_id = unit.id

    # find if same ingredient+unit already exists
    for i, item in enumerate(fridge):
        if item['ingredient_id'] == ingredient.id and item['unit_id'] == target_unit_id:
            target_index = i
            break

    # try to merge other units of same ingredient into target unit
    new_fridge = []
    merged_qty = qty

    for i, item in enumerate(fridge):
        if item['ingredient_id'] != ingredient.id:
            new_fridge.append(item)
            continue

        if item['unit_id'] == target_unit_id:
            merged_qty += item['quantity']
            continue  # will be re-added at the end

        # different unit — try to convert
        try:
            item_unit_conv = IngredientMeasurementUnit.objects.get(
                ingredient=ingredient, unit_id=item['unit_id']
            )
            target_unit_conv = IngredientMeasurementUnit.objects.get(
                ingredient=ingredient, unit=unit
            )
            qty_in_base = item['quantity'] * item_unit_conv.conversion_to_base
            qty_in_target = qty_in_base / target_unit_conv.conversion_to_base
            merged_qty += qty_in_target
        except IngredientMeasurementUnit.DoesNotExist:
            new_fridge.append(item)  # can't convert, keep as separate item

    new_fridge.append({
        'ingredient_id': ingredient.id,
        'unit_id': target_unit_id,
        'quantity': merged_qty,
    })

    request.session['anon_fridge'] = new_fridge
    request.session.modified = True


def subtract_anon_fridge(needed, request):
    anon_fridge = request.session.get('anon_fridge', [])
    final_needed = {}

    for ing_id, data in needed.items():
        ing = data['ingredient']
        base_unit = data['unit']
        needed_qty = data['total_qty']
        available_in_base = 0

        for fridge_item in anon_fridge:
            if fridge_item['ingredient_id'] != ing.id:
                continue
            converted = convert_qty_to_unit(
                fridge_item['quantity'],
                MeasurementUnit.objects.get(id=fridge_item['unit_id']),
                base_unit,
                ing
            )
            if converted is not None:
                available_in_base += converted

        shortfall = needed_qty - available_in_base
        if shortfall > 0:
            final_needed[ing_id] = {
                'ingredient': ing,
                'quantity': round(shortfall, 4),
                'unit': base_unit,
                'by_recipe': data['by_recipe'],
            }

    return final_needed