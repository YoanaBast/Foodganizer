from planner.models import UserFridge
from planner.services.fridge_storage import DbFridge, SessionFridge, get_fridge
from planner.tests import BaseConversionTestCase, attach_session


class FridgeContract:
    """Same behaviour for every storage backend."""

    def make_fridge(self):
        raise NotImplementedError

    def rows(self):
        raise NotImplementedError

    def test_add_same_unit_sums(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        f.add(self.milk, 50, self.ml)
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 150.0)})

    def test_add_other_unit_merges_into_new_unit(self):
        f = self.make_fridge()
        f.add(self.milk, 1, self.cup)
        f.add(self.milk, 60, self.ml)
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 300.0)})

    def test_consume_partial(self):
        f = self.make_fridge()
        f.add(self.milk, 500, self.ml)
        f.consume(self.milk.id, 200, self.ml.id)
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 300.0)})

    def test_consume_all_removes_row(self):
        f = self.make_fridge()
        f.add(self.milk, 240, self.ml)
        f.consume(self.milk.id, 1, self.cup.id)
        self.assertEqual(self.rows(), set())

    def test_clear(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        f.add(self.chicken, 100, self.g)
        f.clear()
        self.assertEqual(self.rows(), set())

    def test_other_ingredients_untouched(self):
        f = self.make_fridge()
        f.add(self.chicken, 100, self.g)
        f.add(self.milk, 100, self.ml)
        f.consume(self.milk.id, 100, self.ml.id)
        self.assertEqual(self.rows(), {(self.chicken.id, self.g.id, 100.0)})

    def test_missing_shortfall(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        needed = {self.milk.id: {
            'ingredient': self.milk, 'unit': self.ml,
            'total_qty': 250, 'by_recipe': {},
        }}
        result = f.missing(needed)
        self.assertEqual(result[self.milk.id]['quantity'], 150.0)

    def test_missing_empty_when_covered(self):
        f = self.make_fridge()
        f.add(self.milk, 1, self.cup)
        needed = {self.milk.id: {
            'ingredient': self.milk, 'unit': self.ml,
            'total_qty': 200, 'by_recipe': {},
        }}
        self.assertEqual(f.missing(needed), {})

    def _ref(self, f, ingredient):
        return [e['ref'] for e in f.all_entries() if e['ingredient_id'] == ingredient.id][0]

    def test_delete_by_ref(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        f.add(self.chicken, 100, self.g)
        f.delete(self._ref(f, self.milk))
        self.assertEqual(self.rows(), {(self.chicken.id, self.g.id, 100.0)})

    def test_update_by_ref(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        f.update(self._ref(f, self.milk), 55, self.ml.id)
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 55.0)})

    def test_delete_bad_ref_is_noop(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        f.delete(99999)
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 100.0)})

    def test_resolved_returns_objects(self):
        f = self.make_fridge()
        f.add(self.milk, 100, self.ml)
        row = f.resolved()[0]
        self.assertEqual(row['ingredient'], self.milk)
        self.assertEqual(row['unit'], self.ml)
        self.assertEqual(row['quantity'], 100.0)

    def test_limit_blocks_new_ingredient_but_not_existing(self):
        from ingredients.models import Ingredient
        from planner.services.fridge_storage import StockLimitExceeded
        egg = Ingredient.objects.create(
            name='limit test ingredient', base_quantity=100, default_unit=self.g,
            base_quantity_kcal=1, base_quantity_protein=1,
            base_quantity_carbs=1, base_quantity_fat=1,
        )
        f = self.make_fridge()
        f.max_items = 2
        f.add(self.milk, 100, self.ml)
        f.add(self.chicken, 100, self.g)
        f.add(self.milk, 50, self.ml)  # existing ingredient is fine
        with self.assertRaises(StockLimitExceeded):
            f.add(egg, 1, self.g)


class DbFridgeTests(FridgeContract, BaseConversionTestCase):
    def make_fridge(self):
        return DbFridge(self.user)

    def rows(self):
        return {
            (r.ingredient_id, r.unit_id, round(float(r.quantity), 4))
            for r in UserFridge.objects.filter(user=self.user)
        }


class SessionFridgeTests(FridgeContract, BaseConversionTestCase):
    def setUp(self):
        super().setUp()
        self.request = attach_session(self.factory.get('/'))

    def make_fridge(self):
        return SessionFridge(self.request.session)

    def rows(self):
        return {
            (i['ingredient_id'], i['unit_id'], round(float(i['quantity']), 4))
            for i in self.request.session.get('anon_fridge', [])
        }


class GetFridgeTests(BaseConversionTestCase):
    def test_picks_backend_by_auth(self):
        from django.contrib.auth.models import AnonymousUser
        req = attach_session(self.factory.get('/'))
        req.user = self.user
        self.assertIsInstance(get_fridge(req), DbFridge)
        req.user = AnonymousUser()
        self.assertIsInstance(get_fridge(req), SessionFridge)
