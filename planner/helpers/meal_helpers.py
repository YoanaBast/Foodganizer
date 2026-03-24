from ingredients.models import IngredientMeasurementUnit, MeasurementUnit


def check_fridge_for_recipe(recipe, fridge_items):
    """
    Returns the name of the first ingredient the user is short on, or None if all good.
    fridge_items: QuerySet of UserFridge
    """
    for ri in recipe.recipe_ingredient.select_related('ingredient', 'unit__unit').all():
        fridge_item = fridge_items.filter(ingredient=ri.ingredient).first()
        available_qty = 0
        if fridge_item:
            try:
                fridge_unit_obj = IngredientMeasurementUnit.objects.get(
                    ingredient=ri.ingredient, unit=fridge_item.unit
                )
                available_qty = (fridge_item.quantity * fridge_unit_obj.conversion_to_base) / ri.unit.conversion_to_base
            except IngredientMeasurementUnit.DoesNotExist:
                pass
        if available_qty < ri.quantity:
            return ri.ingredient.name
    return None


def subtract_fridge_for_recipe(recipe, fridge_items):
    """
    Subtracts recipe ingredients from the user's fridge.
    fridge_items: QuerySet of UserFridge
    """
    for ri in recipe.recipe_ingredient.select_related('ingredient', 'unit').all():
        fridge_item = fridge_items.filter(ingredient=ri.ingredient).first()
        if not fridge_item:
            continue
        try:
            fridge_unit_obj = IngredientMeasurementUnit.objects.get(
                ingredient=ri.ingredient, unit=fridge_item.unit
            )
            qty_to_subtract = (ri.quantity * ri.unit.conversion_to_base) / fridge_unit_obj.conversion_to_base
            fridge_item.quantity = round(fridge_item.quantity - qty_to_subtract, 4)
            if fridge_item.quantity <= 0:
                fridge_item.delete()
            else:
                fridge_item.save()
        except IngredientMeasurementUnit.DoesNotExist:
            continue


def check_anon_fridge_for_recipe(recipe, anon_fridge):
    """
    Returns the name of the first ingredient the anon user is short on, or None if all good.
    anon_fridge: list of session dicts
    """
    for ri in recipe.recipe_ingredient.select_related('ingredient', 'unit').all():
        fridge_qty = 0
        for item in anon_fridge:
            if item['ingredient_id'] != ri.ingredient.id:
                continue
            try:
                fridge_unit = MeasurementUnit.objects.get(id=item['unit_id'])
                conv = IngredientMeasurementUnit.objects.get(ingredient=ri.ingredient, unit=fridge_unit)
                fridge_qty = (item['quantity'] * conv.conversion_to_base) / ri.unit.conversion_to_base
            except (MeasurementUnit.DoesNotExist, IngredientMeasurementUnit.DoesNotExist):
                fridge_qty = 0
        if fridge_qty < ri.quantity:
            return ri.ingredient.name
    return None


def subtract_anon_fridge_for_recipe(recipe, request):
    """
    Subtracts recipe ingredients from the anon session fridge.
    """
    anon_fridge = request.session.get('anon_fridge', [])
    recipe_ingredients = {ri.ingredient.id: ri for ri in recipe.recipe_ingredient.select_related('unit').all()}
    new_fridge = []

    for item in anon_fridge:
        ri = recipe_ingredients.get(item['ingredient_id'])
        if not ri:
            new_fridge.append(item)
            continue
        try:
            fridge_unit = MeasurementUnit.objects.get(id=item['unit_id'])
            conv = IngredientMeasurementUnit.objects.get(ingredient=ri.ingredient, unit=fridge_unit)
            qty_to_subtract = (ri.quantity * ri.unit.conversion_to_base) / conv.conversion_to_base
            remaining = round(item['quantity'] - qty_to_subtract, 4)
            if remaining > 0:
                new_fridge.append({**item, 'quantity': remaining})
        except (MeasurementUnit.DoesNotExist, IngredientMeasurementUnit.DoesNotExist):
            new_fridge.append(item)

    request.session['anon_fridge'] = new_fridge
    request.session.modified = True