from planner.models import UserFridge
from planner.services.fridge_storage import DbFridge, SessionFridge
from planner.tests import BaseConversionTestCase, attach_session
from recipes.models import RecipeIngredient


class RecipeFridgeContract:
    """Recipe check/consume behaves the same on every backend."""

    def setUp(self):
        super().setUp()
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.milk, quantity=1, unit=self.milk_cup)

    def make_fridge(self):
        raise NotImplementedError

    def qty(self, ingredient):
        raise NotImplementedError

    def test_check_passes_when_enough(self):
        f = self.make_fridge()
        f.add(self.chicken, 200, self.g)
        f.add(self.milk, 1, self.cup)
        self.assertIsNone(f.first_missing_for_recipe(self.recipe))

    def test_check_fails_when_short(self):
        f = self.make_fridge()
        f.add(self.chicken, 100, self.g)
        f.add(self.milk, 1, self.cup)
        self.assertEqual(f.first_missing_for_recipe(self.recipe), 'chicken breast')

    def test_check_with_unit_conversion(self):
        f = self.make_fridge()
        f.add(self.chicken, 200, self.g)
        f.add(self.milk, 240, self.ml)
        self.assertIsNone(f.first_missing_for_recipe(self.recipe))

    def test_check_fails_when_ingredient_absent(self):
        f = self.make_fridge()
        f.add(self.chicken, 200, self.g)
        self.assertEqual(f.first_missing_for_recipe(self.recipe), 'milk')

    def test_consume_removes_correct_amounts(self):
        f = self.make_fridge()
        f.add(self.chicken, 300, self.g)
        f.add(self.milk, 500, self.ml)
        f.consume_recipe(self.recipe)
        self.assertAlmostEqual(self.qty(self.chicken), 100, places=2)
        self.assertAlmostEqual(self.qty(self.milk), 260, places=2)

    def test_consume_removes_rows_when_empty(self):
        f = self.make_fridge()
        f.add(self.chicken, 200, self.g)
        f.add(self.milk, 240, self.ml)
        f.consume_recipe(self.recipe)
        self.assertIsNone(self.qty(self.chicken))
        self.assertIsNone(self.qty(self.milk))

    def test_consume_oz_when_recipe_uses_g(self):
        f = self.make_fridge()
        f.add(self.chicken, 10, self.oz)
        f.add(self.milk, 1, self.cup)
        f.consume_recipe(self.recipe)
        self.assertAlmostEqual(self.qty(self.chicken), 10 - 200 / 28.35, places=2)


class DbRecipeFridgeTests(RecipeFridgeContract, BaseConversionTestCase):
    def make_fridge(self):
        return DbFridge(self.user)

    def qty(self, ingredient):
        row = UserFridge.objects.filter(user=self.user, ingredient=ingredient).first()
        return float(row.quantity) if row else None


class SessionRecipeFridgeTests(RecipeFridgeContract, BaseConversionTestCase):
    def setUp(self):
        super().setUp()
        self.request = attach_session(self.factory.get('/'))

    def make_fridge(self):
        return SessionFridge(self.request.session)

    def qty(self, ingredient):
        for i in self.request.session.get('anon_fridge', []):
            if i['ingredient_id'] == ingredient.id:
                return float(i['quantity'])
        return None
