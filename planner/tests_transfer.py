from planner.helpers import transfer_session_to_user
from planner.models import UserBiometrics, UserFridge, UserGroceryList, UserMealList
from planner.services.fridge_storage import SessionFridge
from planner.services.grocery_storage import SessionGrocery
from planner.tests import BaseConversionTestCase, attach_session


class TransferSessionTests(BaseConversionTestCase):
    def setUp(self):
        super().setUp()
        self.session = attach_session(self.factory.get('/')).session

    def test_fridge_and_grocery_move_and_session_clears(self):
        SessionFridge(self.session).add(self.milk, 100, self.ml)
        SessionGrocery(self.session).add(self.chicken, 200, self.g)
        transfer_session_to_user(self.user, self.session)
        self.assertEqual(UserFridge.objects.get(user=self.user).quantity, 100)
        self.assertEqual(UserGroceryList.objects.get(user=self.user).quantity, 200)
        self.assertNotIn('anon_fridge', self.session)
        self.assertNotIn('anon_grocery', self.session)

    def test_merges_with_existing_db_stock_across_units(self):
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=1, unit=self.cup)
        SessionFridge(self.session).add(self.milk, 60, self.ml)
        transfer_session_to_user(self.user, self.session)
        row = UserFridge.objects.get(user=self.user, ingredient=self.milk)
        self.assertEqual(row.unit, self.ml)
        self.assertAlmostEqual(row.quantity, 300.0, places=2)

    def test_meals_and_biometrics(self):
        self.session['anon_meals'] = [{'recipe_id': self.recipe.id, 'recipe_name': 'x', 'made_at': 'now'}]
        self.session['anon_biometrics'] = {
            'gender': 'M', 'age': 30, 'weight_kg': 80, 'height_cm': 180, 'activity_level': 'light'}
        transfer_session_to_user(self.user, self.session)
        self.assertEqual(UserMealList.objects.filter(user=self.user).count(), 1)
        self.assertEqual(UserBiometrics.objects.get(user=self.user).age, 30)
