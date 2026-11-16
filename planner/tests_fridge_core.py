from django.test import SimpleTestCase

from planner.services import fridge_core as core

F = {1: 1000, 2: 1}  # unit 1 = kg-like, unit 2 = g-like


class MergeStockTests(SimpleTestCase):
    def test_same_unit_adds(self):
        r = core.merge_stock([{'unit_id': 2, 'quantity': 100}], 50, 2, F)
        self.assertEqual(r, [{'unit_id': 2, 'quantity': 150.0}])

    def test_converts_other_unit(self):
        r = core.merge_stock([{'unit_id': 2, 'quantity': 500}], 1, 1, F)
        self.assertEqual(r, [{'unit_id': 1, 'quantity': 1.5}])

    def test_unconvertible_kept_separate(self):
        r = core.merge_stock([{'unit_id': 9, 'quantity': 3}], 1, 1, F)
        self.assertIn({'unit_id': 9, 'quantity': 3.0}, r)
        self.assertIn({'unit_id': 1, 'quantity': 1.0}, r)


class SubtractStockTests(SimpleTestCase):
    def test_partial(self):
        r = core.subtract_stock([{'unit_id': 2, 'quantity': 500}], 200, 2, F)
        self.assertEqual(r, [{'unit_id': 2, 'quantity': 300.0}])

    def test_removes_when_empty(self):
        self.assertEqual(core.subtract_stock([{'unit_id': 2, 'quantity': 500}], 500, 2, F), [])

    def test_cross_unit(self):
        r = core.subtract_stock([{'unit_id': 1, 'quantity': 1}], 250, 2, F)
        self.assertEqual(r, [{'unit_id': 1, 'quantity': 0.75}])

    def test_unknown_unit_noop(self):
        e = [{'unit_id': 2, 'quantity': 5}]
        self.assertEqual(core.subtract_stock(e, 1, 99, F), e)


class ShortfallTests(SimpleTestCase):
    def test_covered(self):
        self.assertEqual(core.shortfall(100, 150), 0)

    def test_missing(self):
        self.assertEqual(core.shortfall(100, 40), 60.0)
