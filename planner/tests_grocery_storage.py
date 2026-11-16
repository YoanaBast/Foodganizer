from planner.models import UserFridge, UserGroceryList
from planner.services.fridge_storage import DbFridge, SessionFridge
from planner.services.grocery_storage import DbGrocery, SessionGrocery
from planner.tests import BaseConversionTestCase, attach_session


class GroceryContract:
    def make_grocery(self):
        raise NotImplementedError

    def make_fridge(self):
        raise NotImplementedError

    def rows(self):
        raise NotImplementedError

    def fridge_rows(self):
        raise NotImplementedError

    def needed(self, ingredient, unit, qty):
        return {ingredient.id: {
            'ingredient': ingredient, 'unit': unit,
            'quantity': qty, 'by_recipe': {},
        }}

    def test_add_needed_creates_entry(self):
        self.make_grocery().add_needed(self.needed(self.milk, self.ml, 200))
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 200.0)})

    def test_add_needed_same_unit_accumulates(self):
        g = self.make_grocery()
        g.add_needed(self.needed(self.milk, self.ml, 200))
        g.add_needed(self.needed(self.milk, self.ml, 100))
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 300.0)})

    def test_add_needed_converts_other_unit(self):
        g = self.make_grocery()
        g.add_needed(self.needed(self.milk, self.cup, 1))
        g.add_needed(self.needed(self.milk, self.ml, 60))
        self.assertEqual(self.rows(), {(self.milk.id, self.ml.id, 300.0)})

    def test_move_all_to_fridge(self):
        g, f = self.make_grocery(), self.make_fridge()
        g.add_needed(self.needed(self.milk, self.ml, 200))
        g.add_needed(self.needed(self.chicken, self.g, 100))
        f.add(self.milk, 50, self.ml)
        g.move_all_to(f)
        self.assertEqual(self.rows(), set())
        self.assertEqual(self.fridge_rows(), {
            (self.milk.id, self.ml.id, 250.0),
            (self.chicken.id, self.g.id, 100.0),
        })


class DbGroceryTests(GroceryContract, BaseConversionTestCase):
    def make_grocery(self):
        return DbGrocery(self.user)

    def make_fridge(self):
        return DbFridge(self.user)

    def rows(self):
        return {(r.ingredient_id, r.unit_id, round(float(r.quantity), 4))
                for r in UserGroceryList.objects.filter(user=self.user)}

    def fridge_rows(self):
        return {(r.ingredient_id, r.unit_id, round(float(r.quantity), 4))
                for r in UserFridge.objects.filter(user=self.user)}


class SessionGroceryTests(GroceryContract, BaseConversionTestCase):
    def setUp(self):
        super().setUp()
        self.request = attach_session(self.factory.get('/'))

    def make_grocery(self):
        return SessionGrocery(self.request.session)

    def make_fridge(self):
        return SessionFridge(self.request.session)

    def rows(self):
        return {(i['ingredient_id'], i['unit_id'], round(float(i['quantity']), 4))
                for i in self.request.session.get('anon_grocery', [])}

    def fridge_rows(self):
        return {(i['ingredient_id'], i['unit_id'], round(float(i['quantity']), 4))
                for i in self.request.session.get('anon_fridge', [])}
