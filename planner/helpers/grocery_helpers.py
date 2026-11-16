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

from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from ingredients.models import Ingredient, MeasurementUnit, IngredientCategory, IngredientDietaryTag
from planner.models import UserFridge, UserGroceryList


def redirect_back(request, default):
    nxt = request.POST.get('next', '')
    if nxt and url_has_allowed_host_and_scheme(
            nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(nxt)
    return redirect(default)


def get_grocery_items(request):
    if request.user.is_authenticated:
        return UserGroceryList.objects.filter(user=request.user).select_related('ingredient', 'unit')

    from planner.services.grocery_storage import get_grocery
    return get_grocery(request).resolved()


def get_fridge_context(request):
    g = request.GET
    search = g.get('f_search', '')
    category = g.get('f_category', '')
    tags = [t for t in g.getlist('f_tag') if t]
    sort = g.get('f_sort', '')

    ctx = {
        'ingredients': Ingredient.objects.prefetch_related('measurement_units__unit'),
        'f_search': search,
        'f_selected_category': category,
        'f_selected_tags': tags,
        'f_selected_sort': sort,
        'fridge_categories': IngredientCategory.objects.all().order_by('name'),
    }

    if request.user.is_authenticated:
        qs = UserFridge.objects.filter(user=request.user).select_related(
            'ingredient__category', 'ingredient__default_unit', 'unit'
        ).prefetch_related('ingredient__dietary_tag')

        if search:
            qs = qs.filter(ingredient__name__icontains=search)
        if category:
            qs = qs.filter(ingredient__category__id=category)
        if tags:
            for tag_id in tags:
                qs = qs.filter(ingredient__dietary_tag__id=tag_id)
            qs = qs.distinct()

        order = {
            'qty_asc': 'quantity', 'qty_desc': '-quantity',
            'kcal_asc': 'ingredient__base_quantity_kcal',
            'kcal_desc': '-ingredient__base_quantity_kcal',
        }.get(sort, 'ingredient__name')
        qs = qs.order_by(order)

        page = Paginator(qs, 10).get_page(g.get('f_page'))
        ctx['fridge'] = page
        ctx['fridge_page'] = page
    else:
        from planner.services.fridge_storage import get_fridge
        ctx['anon_fridge'] = get_fridge(request).resolved()
    return ctx