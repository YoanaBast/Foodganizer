from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from planner import tests as base_tests  # module ref, so the base class isn't collected twice
from planner.models import CalendarEntry, UserBiometrics
from recipes.models import RecipeIngredient


class CalendarNutrientRangeViewTests(base_tests.BaseConversionTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        # recipe: 2 servings, so 1 serving = 165 kcal / 31 g protein
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)

    def _bio(self):
        # protein need = 0.8 * 80 = 64 g/day
        return UserBiometrics.objects.create(
            user=self.user, gender='M', age=30, weight_kg=80, height_cm=180, activity_level='sedentary')

    def _log(self, day):
        CalendarEntry.objects.create(user=self.user, date=date(2026, 3, day), recipe=self.recipe, servings=1)

    def _get(self, start='2026-03-10', end='2026-03-12', fill=False, expect=200):
        r = self.client.get(reverse('calendar_nutrients'),
                            {'start': start, 'end': end, 'fill_empty': str(fill).lower()})
        self.assertEqual(r.status_code, expect)
        return r.json()

    def _protein(self, data):
        return {r['nutrient']: r for r in data['rows']}['protein']

    def test_sums_range_without_fill(self):
        self._bio()
        self._log(10)
        self._log(11)
        data = self._get()
        self.assertEqual(data['days'], 3)
        self.assertEqual(data['logged_days'], 2)
        p = self._protein(data)
        self.assertAlmostEqual(p['intake'], 62, places=1)
        self.assertAlmostEqual(p['need'], 192, places=1)      # 64 * 3 days
        self.assertEqual(p['percent'], 32)
        self.assertEqual(p['status'], 'deficient')
        self.assertAlmostEqual(p['avg_per_day'], 20.67, places=2)
        self.assertAlmostEqual(p['daily_need'], 64, places=1)
        self.assertEqual(p['label'], 'Protein')

    def test_fill_empty_counts_empty_days_as_met(self):
        self._bio()
        self._log(10)
        self._log(11)
        data = self._get(fill=True)
        p = self._protein(data)
        self.assertAlmostEqual(p['intake'], 62 + 64, places=1)
        self.assertEqual(p['percent'], 66)                    # 126 / 192
        self.assertTrue(data['fill_empty'])

    def test_entries_outside_range_are_ignored(self):
        self._bio()
        self._log(10)
        self._log(20)
        data = self._get()
        self.assertEqual(data['logged_days'], 1)
        self.assertAlmostEqual(self._protein(data)['intake'], 31, places=1)

    def test_rows_exclude_kcal_and_flag_limits(self):
        self._bio()
        rows = {r['nutrient']: r for r in self._get()['rows']}
        self.assertNotIn('kcal', rows)
        self.assertTrue(rows['sugar']['limit'])

    def test_no_biometrics(self):
        self._log(10)
        self.assertEqual(self._get(), {'error': 'no_biometrics'})

    def test_bad_input(self):
        self._bio()
        self.assertEqual(self.client.get(reverse('calendar_nutrients')).status_code, 400)
        self._get(start='nope', end='2026-03-12', expect=400)
        self._get(start='2026-03-12', end='2026-03-10', expect=400)
        self._get(start='2025-01-01', end='2026-03-10', expect=400)   # over the 366-day cap

    def test_no_extra_queries_per_entry(self):
        self._bio()

        def count(n_entries):
            CalendarEntry.objects.all().delete()
            for i in range(n_entries):
                CalendarEntry.objects.create(
                    user=self.user, date=date(2026, 3, 1 + i), ingredient=self.milk,
                    ingredient_unit=self.cup, quantity=1)
            with CaptureQueriesContext(connection) as ctx:
                self._get(start='2026-03-01', end='2026-03-31')
            return len(ctx)

        self.assertEqual(count(1), count(6))
