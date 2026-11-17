"""Per-entry nutrient totals for calendar entries.

DB-aware, so it lives apart from nutrition_needs_core. Build one EntryNutrients
per request: it caches per-serving recipe nutrients and batch-loads the
ingredient/unit conversions that CalendarEntry.kcal fetches one query at a time.
"""
from core.constants import NUTRIENTS
from ingredients.models import IngredientMeasurementUnit


class EntryNutrients:
    def __init__(self, entries):
        self._recipes = {}
        ing_ids = {e.ingredient_id for e in entries if e.ingredient_id and e.ingredient_unit_id}
        self._imu = {}
        if ing_ids:
            qs = IngredientMeasurementUnit.objects.filter(
                ingredient_id__in=ing_ids
            ).select_related('unit')
            self._imu = {(i.ingredient_id, i.unit_id): i for i in qs}

    def for_entry(self, entry):
        """{nutrient: amount} for one CalendarEntry; all zeros if it can't be resolved."""
        if entry.recipe_id and entry.servings:
            if entry.recipe_id not in self._recipes:
                self._recipes[entry.recipe_id] = entry.recipe.nutrients_per_serving
            per = self._recipes[entry.recipe_id]
            return {n: round(per.get(n, 0) * entry.servings, 2) for n in NUTRIENTS}

        if entry.ingredient_id and entry.quantity and entry.ingredient_unit_id:
            imu = self._imu.get((entry.ingredient_id, entry.ingredient_unit_id))
            if imu is not None:
                got = entry.ingredient.get_nutrients_dict(imu, entry.quantity)
                return {n: round(got.get(n, 0), 2) for n in NUTRIENTS}

        return {n: 0.0 for n in NUTRIENTS}
