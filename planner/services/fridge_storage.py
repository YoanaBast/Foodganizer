from abc import ABC, abstractmethod

from django.db import transaction

from ingredients.models import IngredientMeasurementUnit
from planner.models import UserFridge
from planner.services import fridge_core as core

SESSION_KEY = 'anon_fridge'


def unit_factors(ingredient_id):
    """{unit_id: conversion_to_base}, one query."""
    return dict(
        IngredientMeasurementUnit.objects
        .filter(ingredient_id=ingredient_id)
        .values_list('unit_id', 'conversion_to_base')
    )


class FridgeStorage(ABC):
    """Subclasses only persist. All logic lives in fridge_core."""

    @abstractmethod
    def entries(self, ingredient_id):
        """[{'unit_id', 'quantity'}] for one ingredient."""

    @abstractmethod
    def replace(self, ingredient_id, entries):
        """Overwrite all rows of one ingredient with entries."""

    @abstractmethod
    def clear(self):
        """Remove everything."""

    def add(self, ingredient, qty, unit):
        merged = core.merge_stock(
            self.entries(ingredient.id), qty, unit.id, unit_factors(ingredient.id)
        )
        self.replace(ingredient.id, merged)

    def available(self, ingredient_id, unit_id):
        return core.available_in_unit(
            self.entries(ingredient_id), unit_id, unit_factors(ingredient_id)
        )

    def add_by_ids(self, ingredient_id, qty, unit_id):
        merged = core.merge_stock(
            self.entries(ingredient_id), qty, unit_id, unit_factors(ingredient_id)
        )
        self.replace(ingredient_id, merged)

    def consume(self, ingredient_id, qty, unit_id):
        remaining = core.subtract_stock(
            self.entries(ingredient_id), qty, unit_id, unit_factors(ingredient_id)
        )
        self.replace(ingredient_id, remaining)

    def consume_recipe(self, recipe):
        for ri in recipe.recipe_ingredient.select_related('unit'):
            self.consume(ri.ingredient_id, ri.quantity, ri.unit.unit_id)

    def first_missing_for_recipe(self, recipe):
        """Name of the first ingredient the fridge can't cover, or None."""
        for ri in recipe.recipe_ingredient.select_related('ingredient', 'unit'):
            have = self.available(ri.ingredient_id, ri.unit.unit_id)
            if core.shortfall(ri.quantity, have) > 0:
                return ri.ingredient.name
        return None

    def missing(self, needed):
        """needed: {ing_id: {'ingredient','unit','total_qty','by_recipe'}} -> same shape as old subtract_fridge."""
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


class DbFridge(FridgeStorage):
    def __init__(self, user):
        self.user = user

    def _qs(self, ingredient_id):
        return UserFridge.objects.filter(user=self.user, ingredient_id=ingredient_id)

    def entries(self, ingredient_id):
        return [{'unit_id': r.unit_id, 'quantity': r.quantity} for r in self._qs(ingredient_id)]

    @transaction.atomic
    def replace(self, ingredient_id, entries):
        self._qs(ingredient_id).delete()
        UserFridge.objects.bulk_create([
            UserFridge(user=self.user, ingredient_id=ingredient_id,
                       unit_id=e['unit_id'], quantity=e['quantity'])
            for e in entries
        ])

    def clear(self):
        UserFridge.objects.filter(user=self.user).delete()


class SessionFridge(FridgeStorage):
    def __init__(self, session):
        self.session = session

    def _items(self):
        return self.session.get(SESSION_KEY, [])

    def entries(self, ingredient_id):
        return [
            {'unit_id': i['unit_id'], 'quantity': i['quantity']}
            for i in self._items() if i['ingredient_id'] == ingredient_id
        ]

    def replace(self, ingredient_id, entries):
        others = [i for i in self._items() if i['ingredient_id'] != ingredient_id]
        others += [{'ingredient_id': ingredient_id, **e} for e in entries]
        self.session[SESSION_KEY] = others
        self.session.modified = True

    def clear(self):
        self.session[SESSION_KEY] = []
        self.session.modified = True


def get_fridge(request):
    if request.user.is_authenticated:
        return DbFridge(request.user)
    return SessionFridge(request.session)


# Same stock semantics (add / consume / merge units), reused by grocery storage.
StockStorage = FridgeStorage
