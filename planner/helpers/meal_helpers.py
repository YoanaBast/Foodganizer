from ingredients.models import IngredientMeasurementUnit, MeasurementUnit


def check_fridge_for_recipe(recipe, fridge_items):
    """
    Returns the name of the first ingredient the user is short on,
    or None if all ingredients are available.
    """

    fridge_items = list(
        fridge_items.select_related('ingredient', 'unit')
    )

    ingredient_ids = [
        ri.ingredient_id
        for ri in recipe.recipe_ingredient.all()
    ]

    conversions = IngredientMeasurementUnit.objects.filter(
        ingredient_id__in=ingredient_ids
    )

    conversion_map = {
        (c.ingredient_id, c.unit_id): c.conversion_to_base
        for c in conversions
    }

    fridge_map = {
        item.ingredient_id: item
        for item in fridge_items
    }

    for ri in recipe.recipe_ingredient.all():
        fridge_item = fridge_map.get(ri.ingredient_id)

        if not fridge_item:
            return ri.ingredient.name

        conversion = conversion_map.get(
            (ri.ingredient_id, fridge_item.unit_id)
        )

        if not conversion:
            return ri.ingredient.name

        available_qty = (
            fridge_item.quantity
            * conversion
            / ri.unit.conversion_to_base
        )

        if available_qty < ri.quantity:
            return ri.ingredient.name

    return None




def subtract_fridge_for_recipe(recipe, fridge_items):
    """
    Subtracts recipe ingredients from the user's fridge.
    """

    fridge_items = list(
        fridge_items.select_related('ingredient', 'unit')
    )

    ingredient_ids = [
        ri.ingredient_id
        for ri in recipe.recipe_ingredient.all()
    ]

    conversions = IngredientMeasurementUnit.objects.filter(
        ingredient_id__in=ingredient_ids
    )

    conversion_map = {
        (c.ingredient_id, c.unit_id): c.conversion_to_base
        for c in conversions
    }

    fridge_map = {
        item.ingredient_id: item
        for item in fridge_items
    }

    for ri in recipe.recipe_ingredient.all():
        fridge_item = fridge_map.get(ri.ingredient_id)

        if not fridge_item:
            continue

        conversion = conversion_map.get(
            (ri.ingredient_id, fridge_item.unit_id)
        )

        if not conversion:
            continue

        qty_to_subtract = (
            ri.quantity
            * ri.unit.conversion_to_base
            / conversion
        )

        fridge_item.quantity = round(
            fridge_item.quantity - qty_to_subtract,
            4
        )

        if fridge_item.quantity <= 0:
            fridge_item.delete()
        else:
            fridge_item.save()



def get_anon_fridge_data(anon_fridge):
    """
    Preload all measurement units and conversion factors
    needed by the anonymous fridge.
    """

    unit_ids = {
        item['unit_id']
        for item in anon_fridge
        if item.get('unit_id')
    }

    conversions = IngredientMeasurementUnit.objects.filter(
        unit_id__in=unit_ids
    )

    conversion_map = {
        (conversion.ingredient_id, conversion.unit_id):
            conversion.conversion_to_base
        for conversion in conversions
    }

    return conversion_map


def check_anon_fridge_for_recipe(recipe, anon_fridge):
    """
    Returns the name of the first ingredient the anon user
    is short on, or None if all ingredients are available.
    """

    conversion_map = get_anon_fridge_data(anon_fridge)

    # One fridge item per ingredient/unit combination.
    fridge_map = {
        (item['ingredient_id'], item['unit_id']): item['quantity']
        for item in anon_fridge
    }

    for ri in recipe.recipe_ingredient.all():
        fridge_qty = 0

        for (ingredient_id, unit_id), quantity in fridge_map.items():
            if ingredient_id != ri.ingredient_id:
                continue

            if unit_id == ri.unit.unit_id:
                fridge_qty = quantity
            else:
                conversion = conversion_map.get(
                    (ingredient_id, unit_id)
                )

                if conversion:
                    fridge_qty = (
                        quantity
                        * conversion
                        / ri.unit.conversion_to_base
                    )

            break

        if fridge_qty < ri.quantity:
            return ri.ingredient.name

    return None


def subtract_anon_fridge_for_recipe(recipe, request):
    """
    Subtracts recipe ingredients from the anonymous session fridge.
    """

    anon_fridge = request.session.get('anon_fridge', [])

    recipe_ingredients = {
        ri.ingredient_id: ri
        for ri in recipe.recipe_ingredient.all()
    }

    conversion_map = get_anon_fridge_data(anon_fridge)

    new_fridge = []

    for item in anon_fridge:
        ri = recipe_ingredients.get(item['ingredient_id'])

        if not ri:
            new_fridge.append(item)
            continue

        conversion = conversion_map.get(
            (item['ingredient_id'], item['unit_id'])
        )

        if not conversion:
            new_fridge.append(item)
            continue

        qty_to_subtract = (
            ri.quantity
            * ri.unit.conversion_to_base
            / conversion
        )

        remaining = round(
            item['quantity'] - qty_to_subtract,
            4
        )

        if remaining > 0:
            new_fridge.append({
                **item,
                'quantity': remaining,
            })

    request.session['anon_fridge'] = new_fridge
    request.session.modified = True

