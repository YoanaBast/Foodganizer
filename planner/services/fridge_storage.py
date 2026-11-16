from abc import ABC, abstractmethod

from django.db import transaction

from ingredients.models import Ingredient, IngredientMeasurementUnit, MeasurementUnit
from planner.models import UserFridge
from planner.services import fridge_core as core


def unit_factors(ingredient_id):
    """{unit_id: conversion_to_base}, one query."""
    return dict(
        IngredientMeasurementUnit.objects
        .filter(ingredient_id=ingredient_id)
        .values_list('unit_id', 'conversion_to_base')
    )


class StockStorage(ABC):
    """Stock of ingredient quantities. All logic here; subclasses only persist."""

    @abstractmethod
    def entries(self, ingredient_id):
        """[{'unit_id', 'quantity'}] for one ingredient."""

    @abstractmethod
    def replace(self, ingredient_id, entries):
        """Overwrite all rows of one ingredient."""

    @abstractmethod
    def all_entries(self):
        """[{'ref', 'ingredient_id', 'unit_id', 'quantity'}] for everything."""

    @abstractmethod
    def delete(self, ref):
        """Delete one row by ref (DB id or session index)."""

    @abstractmethod
    def update(self, ref, quantity, unit_id):
        """Set quantity and unit of one row by ref."""

    @abstractmethod
    def clear(self):
        """Remove everything."""

    def resolved(self):
        """Entries with real Ingredient/MeasurementUnit objects, for templates."""
        entries = self.all_entries()
        ings = Ingredient.objects.in_bulk({e['ingredient_id'] for e in entries})
        units = MeasurementUnit.objects.in_bulk(
            {e['unit_id'] for e in entries if e.get('unit_id')}
        )
        return [
            {
                'index': e['ref'],
                'ref': e['ref'],
                'ingredient': ings[e['ingredient_id']],
                'unit': units.get(e.get('unit_id')),
                'quantity': e['quantity'],
            }
            for e in entries if e['ingredient_id'] in ings
        ]

    def add(self, ingredient, qty, unit):
        self.add_by_ids(ingredient.id, qty, unit.id if unit else None)

    def add_by_ids(self, ingredient_id, qty, unit_id):
        merged = core.merge_stock(
            self.entries(ingredient_id), qty, unit_id, unit_factors(ingredient_id)
        )
        self.replace(ingredient_id, merged)

    def available(self, ingredient_id, unit_id):
        return core.available_in_unit(
            self.entries(ingredient_id), unit_id, unit_factors(ingredient_id)
        )

    def consume(self, ingredient_id, qty, unit_id):
        remaining = core.subtract_stock(
            self.entries(ingredient_id), qty, unit_id, unit_factors(ingredient_id)
        )
        self.replace(ingredient_id, remaining)

    def consume_recipe(self, recipe):
        for ri in recipe.recipe_ingredient.select_related('unit'):
            self.consume(ri.ingredient_id, ri.quantity, ri.unit.unit_id)

    def first_missing_for_recipe(self, recipe):
        """Name of the first ingredient the stock can't cover, or None."""
        for ri in recipe.recipe_ingredient.select_related('ingredient', 'unit'):
            have = self.available(ri.ingredient_id, ri.unit.unit_id)
            if core.shortfall(ri.quantity, have) > 0:
                return ri.ingredient.name
        return None

    def recipe_matches(self, recipes):
        """How well the stock covers each recipe, best match first. 2 queries total."""
        from collections import defaultdict

        recipes = list(recipes)
        stock = defaultdict(list)
        for e in self.all_entries():
            stock[e['ingredient_id']].append(
                {'unit_id': e['unit_id'], 'quantity': e['quantity']}
            )

        ing_ids = {ri.ingredient_id for r in recipes for ri in r.recipe_ingredient.all()}
        factors = defaultdict(dict)
        for ing_id, unit_id, factor in IngredientMeasurementUnit.objects.filter(
            ingredient_id__in=ing_ids
        ).values_list('ingredient_id', 'unit_id', 'conversion_to_base'):
            factors[ing_id][unit_id] = factor

        results = []
        for recipe in recipes:
            items = [
                {
                    'ingredient_id': ri.ingredient_id,
                    'name': ri.ingredient.name,
                    'quantity': ri.quantity,
                    'unit_id': ri.unit.unit_id,
                    'unit_code': ri.unit.unit.code if ri.unit.unit else '',
                }
                for ri in recipe.recipe_ingredient.all()
            ]
            matched, missing = core.coverage(items, stock, factors)
            total = len(items)
            results.append({
                'recipe': recipe,
                'match_percent': int(matched / total * 100) if total else 0,
                'can_make': total > 0 and matched == total,
                'missing_ingredients': missing,
            })
        results.sort(key=lambda r: r['match_percent'], reverse=True)
        return results

    def missing(self, needed):
        """needed: {ing_id: {'ingredient','unit','total_qty','by_recipe'}}"""
        final = {}
        for ing_id, data in needed.items():
            short = core.shortfall(
                data['total_qty'], self.available(ing_id, data['unit'].id)
            )
            if short > 0:
                final[ing_id] = {
                    'ingredient': data['ingredient'],
                    'quantity': short,
                    'unit': data['unit'],
                    'by_recipe': data['by_recipe'],
                }
        return final


class DbStock(StockStorage):
    model = None  # set by subclass

    def __init__(self, user):
        self.user = user

    def _qs(self, ingredient_id=None):
        qs = self.model.objects.filter(user=self.user)
        return qs.filter(ingredient_id=ingredient_id) if ingredient_id else qs

    def entries(self, ingredient_id):
        return [{'unit_id': r.unit_id, 'quantity': r.quantity} for r in self._qs(ingredient_id)]

    @transaction.atomic
    def replace(self, ingredient_id, entries):
        self._qs(ingredient_id).delete()
        self.model.objects.bulk_create([
            self.model(user=self.user, ingredient_id=ingredient_id,
                       unit_id=e['unit_id'], quantity=e['quantity'])
            for e in entries
        ])

    def all_entries(self):
        return [
            {'ref': r.id, 'ingredient_id': r.ingredient_id,
             'unit_id': r.unit_id, 'quantity': r.quantity}
            for r in self._qs()
        ]

    def delete(self, ref):
        self._qs().filter(id=ref).delete()

    def update(self, ref, quantity, unit_id):
        self._qs().filter(id=ref).update(quantity=quantity, unit_id=unit_id)

    def clear(self):
        self._qs().delete()


class SessionStock(StockStorage):
    key = None  # set by subclass

    def __init__(self, session):
        self.session = session

    def _items(self):
        return self.session.get(self.key, [])

    def _save(self, items):
        self.session[self.key] = items
        self.session.modified = True

    def entries(self, ingredient_id):
        return [
            {'unit_id': i['unit_id'], 'quantity': i['quantity']}
            for i in self._items() if i['ingredient_id'] == ingredient_id
        ]

    def replace(self, ingredient_id, entries):
        others = [i for i in self._items() if i['ingredient_id'] != ingredient_id]
        others += [{'ingredient_id': ingredient_id, **e} for e in entries]
        self._save(others)

    def all_entries(self):
        return [{'ref': idx, **i} for idx, i in enumerate(self._items())]

    def delete(self, ref):
        items = self._items()
        if 0 <= ref < len(items):
            items.pop(ref)
            self._save(items)

    def update(self, ref, quantity, unit_id):
        items = self._items()
        if 0 <= ref < len(items):
            items[ref]['quantity'] = quantity
            items[ref]['unit_id'] = unit_id
            self._save(items)

    def clear(self):
        self._save([])


class DbFridge(DbStock):
    model = UserFridge


class SessionFridge(SessionStock):
    key = 'anon_fridge'


def get_fridge(request):
    if request.user.is_authenticated:
        return DbFridge(request.user)
    return SessionFridge(request.session)
