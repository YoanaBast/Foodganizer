from django.test import SimpleTestCase

from planner.services import nutrition_needs_core as nn
from planner.services.biometrics_core import summarize


class BmiTests(SimpleTestCase):
    def test_value(self):
        self.assertEqual(nn.bmi(80, 180), 24.7)

    def test_categories(self):
        self.assertEqual(nn.bmi_category(17), 'Underweight')
        self.assertEqual(nn.bmi_category(22), 'Normal')
        self.assertEqual(nn.bmi_category(27), 'Overweight')
        self.assertEqual(nn.bmi_category(31), 'Obese')


class NeedsTests(SimpleTestCase):
    def test_covers_every_nutrient(self):
        from core.constants import NUTRIENTS
        needs = nn.daily_needs('M', 30, 80, 2500)
        self.assertEqual(set(needs), set(NUTRIENTS))

    def test_gender_differences(self):
        self.assertEqual(nn.daily_needs('M', 30, 70, 2000)['vitamin_a'], 900)
        self.assertEqual(nn.daily_needs('F', 30, 70, 2000)['vitamin_a'], 700)
        self.assertEqual(nn.daily_needs('F', 30, 70, 2000)['iron'], 18)
        self.assertEqual(nn.daily_needs('F', 60, 70, 2000)['iron'], 8)

    def test_protein_scales_with_weight(self):
        self.assertEqual(nn.daily_needs('M', 30, 100, 2000)['protein'], 80.0)

    def test_summarize_includes_bmi_and_needs(self):
        r = summarize({'gender': 'M', 'age': 30, 'weight_kg': 80,
                       'height_cm': 180, 'activity_level': 'light'})
        self.assertEqual(r.bmi, 24.7)
        self.assertIn('vitamin_d', r.nutrient_needs)


class CoverageTests(SimpleTestCase):
    def setUp(self):
        self.needs = nn.daily_needs('M', 30, 80, 2500)

    def _row(self, rows, name):
        return next(r for r in rows if r['nutrient'] == name)

    def test_deficient_low_ok(self):
        rows = nn.coverage({'protein': 10, 'vitamin_c': 60, 'zinc': 11}, self.needs)
        self.assertEqual(self._row(rows, 'protein')['status'], 'deficient')
        self.assertEqual(self._row(rows, 'vitamin_c')['status'], 'low')
        self.assertEqual(self._row(rows, 'zinc')['status'], 'ok')

    def test_limits_flag_over(self):
        rows = nn.coverage({'salt': 8}, self.needs)
        self.assertEqual(self._row(rows, 'salt')['status'], 'over')

    def test_kcal_excluded(self):
        self.assertNotIn('kcal', [r['nutrient'] for r in nn.coverage({}, self.needs)])
