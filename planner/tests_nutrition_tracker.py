from datetime import date

from django.db import connection
from django.template import Context, Template
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.constants import NUTRIENTS
from planner import tests as base_tests  # module ref, so the base class isn't collected twice
from planner.models import CalendarEntry, UserBiometrics
from planner.services import nutrition_needs_core as nn
from planner.services.nutrition_tracker import EntryNutrients
from recipes.models import RecipeIngredient


class LabelAndRowsTests(SimpleTestCase):
    def test_labels(self):
        self.assertEqual(nn.nutrient_label('vitamin_b12'), 'Vitamin B12')
        self.assertEqual(nn.nutrient_label('vitamin_a'), 'Vitamin A')
        self.assertEqual(nn.nutrient_label('iron'), 'Iron')

    def test_rows_exclude_kcal_and_flag_limits(self):
        rows = nn.needs_rows(nn.daily_needs('M', 30, 80, 2500))
        by_name = {r['nutrient']: r for r in rows}
        self.assertNotIn('kcal', by_name)
        self.assertEqual(len(rows), len(NUTRIENTS) - 1)
        self.assertTrue(by_name['sugar']['limit'])
        self.assertTrue(by_name['salt']['limit'])
        self.assertTrue(by_name['cholesterol']['limit'])
        self.assertFalse(by_name['protein']['limit'])
        self.assertEqual(by_name['protein']['unit'], 'g')


class EntryNutrientsTests(base_tests.BaseConversionTestCase):
    D = date(2026, 3, 10)

    def _entry(self, **kw):
        return CalendarEntry.objects.create(user=self.user, date=self.D, **kw)

    def test_recipe_entry_scales_by_servings(self):
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)
        # recipe has 2 servings: total 330 kcal / 62 g protein
        e = self._entry(recipe=self.recipe, servings=2)
        got = EntryNutrients([e]).for_entry(e)
        self.assertAlmostEqual(got['kcal'], 330, places=1)
        self.assertAlmostEqual(got['protein'], 62, places=1)
        self.assertEqual(set(got), set(NUTRIENTS))

    def test_ingredient_entry_converts_units(self):
        e = self._entry(ingredient=self.milk, ingredient_unit=self.cup, quantity=1)
        got = EntryNutrients([e]).for_entry(e)
        self.assertAlmostEqual(got['kcal'], 100.8, places=2)      # 42 * 240/100
        self.assertAlmostEqual(got['protein'], 8.16, places=2)

    def test_ingredient_entry_other_unit(self):
        e = self._entry(ingredient=self.chicken, ingredient_unit=self.oz, quantity=1)
        got = EntryNutrients([e]).for_entry(e)
        self.assertAlmostEqual(got['kcal'], 165 * 0.2835, places=1)

    def test_countable_ingredient(self):
        e = self._entry(ingredient=self.egg, ingredient_unit=self.pc, quantity=2)
        self.assertAlmostEqual(EntryNutrients([e]).for_entry(e)['kcal'], 140, places=2)

    def test_matches_calendar_entry_kcal(self):
        e = self._entry(ingredient=self.milk, ingredient_unit=self.cup, quantity=1)
        self.assertAlmostEqual(EntryNutrients([e]).for_entry(e)['kcal'], e.kcal, places=2)

    def test_unresolvable_entries_return_zeros(self):
        # egg has no gram conversion; and an entry with nothing attached
        bad_unit = self._entry(ingredient=self.egg, ingredient_unit=self.g, quantity=5)
        empty = self._entry()
        calc = EntryNutrients([bad_unit, empty])
        for e in (bad_unit, empty):
            got = calc.for_entry(e)
            self.assertEqual(set(got), set(NUTRIENTS))
            self.assertTrue(all(v == 0 for v in got.values()))


class CalendarDataViewTests(base_tests.BaseConversionTestCase):
    D = date(2026, 3, 10)

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)

    def _get(self):
        r = self.client.get(reverse('calendar_data'), {'year': 2026, 'month': 3})
        self.assertEqual(r.status_code, 200)
        return r.json()

    def _bio(self):
        return UserBiometrics.objects.create(
            user=self.user, gender='M', age=30, weight_kg=80, height_cm=180, activity_level='sedentary')

    def test_day_has_nutrients_and_kcal(self):
        CalendarEntry.objects.create(user=self.user, date=self.D, recipe=self.recipe, servings=1)
        day = self._get()['days']['2026-03-10']
        self.assertAlmostEqual(day['kcal'], 165, places=1)
        self.assertAlmostEqual(day['nutrients']['protein'], 31, places=1)
        self.assertAlmostEqual(day['nutrients']['kcal'], day['kcal'], places=2)
        self.assertEqual(day['entries'][0]['name'], 'test recipe')

    def test_no_biometrics_means_no_coverage(self):
        CalendarEntry.objects.create(user=self.user, date=self.D, recipe=self.recipe, servings=1)
        data = self._get()
        self.assertIsNone(data['tdee'])
        self.assertNotIn('coverage', data['days']['2026-03-10'])

    def test_coverage_with_biometrics(self):
        self._bio()
        CalendarEntry.objects.create(user=self.user, date=self.D, recipe=self.recipe, servings=1)
        data = self._get()
        self.assertIsNotNone(data['tdee'])
        rows = {r['nutrient']: r for r in data['days']['2026-03-10']['coverage']}
        self.assertNotIn('kcal', rows)
        protein = rows['protein']          # need = 0.8 * 80 = 64 g, eaten ~31 g
        self.assertEqual(protein['percent'], 48)
        self.assertEqual(protein['status'], 'deficient')
        self.assertEqual(protein['label'], 'Protein')
        self.assertTrue(rows['sugar']['limit'])

    def test_ingredient_entries_do_not_add_queries_per_entry(self):
        def count(n_entries):
            CalendarEntry.objects.all().delete()
            for i in range(n_entries):
                CalendarEntry.objects.create(
                    user=self.user, date=date(2026, 3, 1 + i), ingredient=self.milk,
                    ingredient_unit=self.cup, quantity=1)
            with CaptureQueriesContext(connection) as ctx:
                self._get()
            return len(ctx)

        self.assertEqual(count(1), count(6))


class NutrientNeedsTagTests(base_tests.BaseConversionTestCase):
    def _render(self):
        return Template('{% load nutrition_tags %}{% nutrient_needs user %}').render(Context({'user': self.user}))

    def test_without_biometrics_prompts(self):
        self.assertIn('Set your biometrics', self._render())

    def test_with_biometrics_lists_needs(self):
        UserBiometrics.objects.create(
            user=self.user, gender='F', age=30, weight_kg=60, height_cm=165, activity_level='light')
        html = self._render()
        self.assertIn('BMI', html)
        self.assertIn('Vitamin D', html)
        self.assertIn('max', html)
