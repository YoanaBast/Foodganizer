from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

# Create your tests here. :)


from ingredients.models import (
    Ingredient, MeasurementUnit, IngredientMeasurementUnit, IngredientCategory,
)
from planner.helpers import (
    convert_qty_to_unit,
    get_or_create_fridge_item,
    get_or_create_anon_fridge_item,
    subtract_fridge,
    subtract_anon_fridge,
    build_needed_dict,
)
from planner.helpers import (
    check_fridge_for_recipe,
    subtract_fridge_for_recipe,
    check_anon_fridge_for_recipe,
    subtract_anon_fridge_for_recipe,
)
from planner.helpers.calories_helpers import Tracker, calculate_from_session
from planner.models import UserFridge, UserGroceryList
from recipes.models import Recipe, RecipeIngredient, RecipeCategory

from django.contrib.sessions.middleware import SessionMiddleware


class MockSession(dict):
    """A dict that also supports .modified, mimicking Django's session interface."""
    modified = False


def attach_session(request):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


User = get_user_model()


class BaseConversionTestCase(TestCase):
    """
    Sets up:
    - milk ingredient with default unit = ml (conv=1), cup (conv=240), tbsp (conv=15)
    - chicken ingredient with default unit = g (conv=1), oz (conv=28.35)
    - a test user
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass', email='t@t.com')
        self.factory = RequestFactory()

        self.ml = MeasurementUnit.objects.create(code='ml', name_singular='millilitre', name_plural='millilitres')
        self.cup = MeasurementUnit.objects.create(code='cup', name_singular='cup', name_plural='cups')
        self.tbsp = MeasurementUnit.objects.create(code='tbsp', name_singular='tablespoon', name_plural='tablespoons')
        self.g = MeasurementUnit.objects.create(code='g', name_singular='gram', name_plural='grams')
        self.oz = MeasurementUnit.objects.create(code='oz', name_singular='ounce', name_plural='ounces')
        self.pc = MeasurementUnit.objects.create(code='pc', name_singular='piece', name_plural='pieces')

        self.milk = Ingredient.objects.create(
            name='milk', base_quantity=100, default_unit=self.ml,
            base_quantity_kcal=42, base_quantity_protein=3.4,
            base_quantity_carbs=5.0, base_quantity_fat=1.0,
        )
        # save() auto-created milk_ml with conversion=1, just fetch it
        self.milk_ml = IngredientMeasurementUnit.objects.get(ingredient=self.milk, unit=self.ml)
        self.milk_cup = IngredientMeasurementUnit.objects.create(
            ingredient=self.milk, unit=self.cup, conversion_to_base=240
        )
        self.milk_tbsp = IngredientMeasurementUnit.objects.create(
            ingredient=self.milk, unit=self.tbsp, conversion_to_base=15
        )

        self.chicken = Ingredient.objects.create(
            name='chicken breast', base_quantity=100, default_unit=self.g,
            base_quantity_kcal=165, base_quantity_protein=31,
            base_quantity_carbs=0, base_quantity_fat=3.6,
        )
        # save() auto-created chicken_g, just fetch it
        self.chicken_g = IngredientMeasurementUnit.objects.get(ingredient=self.chicken, unit=self.g)
        self.chicken_oz = IngredientMeasurementUnit.objects.create(
            ingredient=self.chicken, unit=self.oz, conversion_to_base=28.35
        )

        self.egg = Ingredient.objects.create(
            name='egg', base_quantity=1, default_unit=self.pc,
            base_quantity_kcal=70, base_quantity_protein=6,
        )
        # save() auto-created egg_pc, just fetch it
        self.egg_pc = IngredientMeasurementUnit.objects.get(ingredient=self.egg, unit=self.pc)

        self.category = RecipeCategory.objects.create(name='test category')
        self.recipe = Recipe.objects.create(
            name='test recipe', instructions='test', servings=2,
            created_by=self.user, updated_by=self.user,
        )


class ConvertQtyToUnitTests(BaseConversionTestCase):

    def test_same_unit_returns_same_qty(self):
        result = convert_qty_to_unit(100, self.ml, self.ml, self.milk)
        self.assertEqual(result, 100)

    def test_ml_to_cup(self):
        result = convert_qty_to_unit(240, self.ml, self.cup, self.milk)
        self.assertAlmostEqual(result, 1.0, places=4)

    def test_cup_to_ml(self):
        result = convert_qty_to_unit(1, self.cup, self.ml, self.milk)
        self.assertAlmostEqual(result, 240.0, places=4)

    def test_cup_to_tbsp(self):
        # 1 cup = 240ml base, 1 tbsp = 15ml base → 240/15 = 16 tbsp
        result = convert_qty_to_unit(1, self.cup, self.tbsp, self.milk)
        self.assertAlmostEqual(result, 16.0, places=4)

    def test_tbsp_to_cup(self):
        result = convert_qty_to_unit(16, self.tbsp, self.cup, self.milk)
        self.assertAlmostEqual(result, 1.0, places=4)

    def test_g_to_oz(self):
        result = convert_qty_to_unit(28.35, self.g, self.oz, self.chicken)
        self.assertAlmostEqual(result, 1.0, places=2)

    def test_oz_to_g(self):
        result = convert_qty_to_unit(1, self.oz, self.g, self.chicken)
        self.assertAlmostEqual(result, 28.35, places=2)

    def test_incompatible_units_returns_none(self):
        result = convert_qty_to_unit(1, self.cup, self.g, self.chicken)
        self.assertIsNone(result)

    def test_partial_cup_to_ml(self):
        result = convert_qty_to_unit(0.5, self.cup, self.ml, self.milk)
        self.assertAlmostEqual(result, 120.0, places=4)


class FridgeMergingTests(BaseConversionTestCase):

    def _make_request(self):
        request = self.factory.get('/')
        attach_session(request)
        request.user = self.user
        return request

    def test_add_new_item_creates_fridge_entry(self):
        request = self._make_request()
        get_or_create_fridge_item(request, self.milk, 100, self.ml)
        item = UserFridge.objects.get(user=self.user, ingredient=self.milk)
        self.assertAlmostEqual(item.quantity, 100)
        self.assertEqual(item.unit, self.ml)

    def test_add_same_unit_accumulates(self):
        request = self._make_request()
        get_or_create_fridge_item(request, self.milk, 100, self.ml)
        get_or_create_fridge_item(request, self.milk, 50, self.ml)
        item = UserFridge.objects.get(user=self.user, ingredient=self.milk)
        self.assertAlmostEqual(item.quantity, 150)

    def test_add_different_unit_merges_into_target(self):
        # Have 100ml, add 1 cup → merge to cups: 100/240 + 1 cups
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=100, unit=self.ml)
        request = self._make_request()
        get_or_create_fridge_item(request, self.milk, 1, self.cup)
        items = UserFridge.objects.filter(user=self.user, ingredient=self.milk)
        self.assertEqual(items.count(), 1)
        item = items.first()
        self.assertEqual(item.unit, self.cup)
        self.assertAlmostEqual(item.quantity, 1 + 100/240, places=3)

    def test_add_cup_when_have_ml_and_tbsp(self):
        # 100ml + 2 tbsp + 1 cup → all in cups
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=100, unit=self.ml)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=2, unit=self.tbsp)
        request = self._make_request()
        get_or_create_fridge_item(request, self.milk, 1, self.cup)
        items = UserFridge.objects.filter(user=self.user, ingredient=self.milk)
        self.assertEqual(items.count(), 1)
        expected = 1 + 100/240 + 30/240
        self.assertAlmostEqual(items.first().quantity, expected, places=3)


class AnonFridgeMergingTests(BaseConversionTestCase):

    def _make_request(self, session=None):
        request = self.factory.get('/')
        request.session = MockSession(session or {})
        return request

    def test_add_new_item_to_empty_fridge(self):
        request = self._make_request()
        get_or_create_anon_fridge_item(request, self.milk, 100, self.ml)
        fridge = request.session['anon_fridge']
        self.assertEqual(len(fridge), 1)
        self.assertEqual(fridge[0]['quantity'], 100)

    def test_add_same_unit_accumulates(self):
        session = {'anon_fridge': [{'ingredient_id': self.milk.id, 'unit_id': self.ml.id, 'quantity': 100}]}
        request = self._make_request(session)
        get_or_create_anon_fridge_item(request, self.milk, 50, self.ml)
        fridge = request.session['anon_fridge']
        self.assertEqual(len(fridge), 1)
        self.assertAlmostEqual(fridge[0]['quantity'], 150)

    def test_add_cup_when_have_ml_merges(self):
        # 100ml + 1 cup → 1 + 100/240 cups
        session = {'anon_fridge': [{'ingredient_id': self.milk.id, 'unit_id': self.ml.id, 'quantity': 100}]}
        request = self._make_request(session)
        get_or_create_anon_fridge_item(request, self.milk, 1, self.cup)
        fridge = request.session['anon_fridge']
        self.assertEqual(len(fridge), 1)
        self.assertEqual(fridge[0]['unit_id'], self.cup.id)
        self.assertAlmostEqual(fridge[0]['quantity'], 1 + 100/240, places=3)

    def test_incompatible_units_kept_separate(self):
        session = {'anon_fridge': [{'ingredient_id': self.chicken.id, 'unit_id': self.g.id, 'quantity': 100}]}
        request = self._make_request(session)
        get_or_create_anon_fridge_item(request, self.chicken, 1, self.cup)
        self.assertEqual(len(request.session['anon_fridge']), 2)

    def test_different_ingredients_not_merged(self):
        session = {'anon_fridge': [{'ingredient_id': self.milk.id, 'unit_id': self.ml.id, 'quantity': 100}]}
        request = self._make_request(session)
        get_or_create_anon_fridge_item(request, self.chicken, 200, self.g)
        self.assertEqual(len(request.session['anon_fridge']), 2)


class SubtractFridgeTests(BaseConversionTestCase):

    def _make_request(self):
        request = self.factory.get('/')
        attach_session(request)
        request.user = self.user
        return request

    def _make_needed(self, ingredient, unit, total_qty):
        return {
            ingredient.id: {
                'ingredient': ingredient,
                'unit': unit,
                'total_qty': total_qty,
                'by_recipe': {},
            }
        }

    def test_no_fridge_returns_full_shortfall(self):
        needed = self._make_needed(self.chicken, self.g, 200)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertAlmostEqual(result[self.chicken.id]['quantity'], 200)

    def test_exact_fridge_quantity_removes_from_list(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=200, unit=self.g)
        needed = self._make_needed(self.chicken, self.g, 200)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertNotIn(self.chicken.id, result)

    def test_partial_fridge_returns_shortfall(self):
        # 100g in fridge, need 200g → 100g on list
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=100, unit=self.g)
        needed = self._make_needed(self.chicken, self.g, 200)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertAlmostEqual(result[self.chicken.id]['quantity'], 100, places=2)

    def test_fridge_in_different_unit_converts_correctly(self):
        # 1 cup milk (240ml) in fridge, need 300ml → shortfall 60ml
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=1, unit=self.cup)
        needed = self._make_needed(self.milk, self.ml, 300)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertAlmostEqual(result[self.milk.id]['quantity'], 60, places=2)

    def test_more_in_fridge_than_needed_not_on_list(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=500, unit=self.g)
        needed = self._make_needed(self.chicken, self.g, 200)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertNotIn(self.chicken.id, result)

    def test_fridge_oz_subtracted_from_g_needed(self):
        # 2oz = 56.7g, need 100g → shortfall 43.3g
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=2, unit=self.oz)
        needed = self._make_needed(self.chicken, self.g, 100)
        fridge_items = UserFridge.objects.filter(user=self.user)
        result = subtract_fridge(needed, fridge_items, self._make_request())
        self.assertAlmostEqual(result[self.chicken.id]['quantity'], 100 - 56.7, places=1)


class RecipeFridgeTests(BaseConversionTestCase):

    def setUp(self):
        super().setUp()
        self.ri_chicken = RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.chicken,
            quantity=200, unit=self.chicken_g,
        )
        self.ri_milk = RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.milk,
            quantity=1, unit=self.milk_cup,
        )

    def test_check_fridge_passes_when_enough(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=200, unit=self.g)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=1, unit=self.cup)
        result = check_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        self.assertIsNone(result)

    def test_check_fridge_fails_when_short(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=100, unit=self.g)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=1, unit=self.cup)
        result = check_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        self.assertEqual(result, 'chicken breast')

    def test_check_fridge_with_unit_conversion(self):
        # 240ml milk = 1 cup, recipe needs 1 cup → should pass
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=200, unit=self.g)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=240, unit=self.ml)
        result = check_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        self.assertIsNone(result)

    def test_subtract_fridge_removes_correct_amounts(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=300, unit=self.g)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=500, unit=self.ml)
        subtract_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        self.assertAlmostEqual(UserFridge.objects.get(user=self.user, ingredient=self.chicken).quantity, 100, places=2)
        self.assertAlmostEqual(UserFridge.objects.get(user=self.user, ingredient=self.milk).quantity, 260, places=2)

    def test_subtract_fridge_deletes_when_empty(self):
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=200, unit=self.g)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=240, unit=self.ml)
        subtract_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        self.assertFalse(UserFridge.objects.filter(user=self.user, ingredient=self.chicken).exists())
        self.assertFalse(UserFridge.objects.filter(user=self.user, ingredient=self.milk).exists())

    def test_subtract_fridge_oz_when_recipe_uses_g(self):
        # 10oz chicken, recipe needs 200g → 10 - 200/28.35 oz remaining
        UserFridge.objects.create(user=self.user, ingredient=self.chicken, quantity=10, unit=self.oz)
        UserFridge.objects.create(user=self.user, ingredient=self.milk, quantity=1, unit=self.cup)
        subtract_fridge_for_recipe(self.recipe, UserFridge.objects.filter(user=self.user))
        chicken_item = UserFridge.objects.get(user=self.user, ingredient=self.chicken)
        self.assertAlmostEqual(chicken_item.quantity, 10 - 200/28.35, places=2)


class AnonRecipeFridgeTests(BaseConversionTestCase):

    def setUp(self):
        super().setUp()
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.chicken,
            quantity=200, unit=self.chicken_g,
        )

    def _make_request(self, anon_fridge):
        request = self.factory.get('/')
        request.session = MockSession({'anon_fridge': anon_fridge})
        return request

    def test_check_anon_fridge_passes(self):
        result = check_anon_fridge_for_recipe(
            self.recipe,
            [{'ingredient_id': self.chicken.id, 'unit_id': self.g.id, 'quantity': 200}]
        )
        self.assertIsNone(result)

    def test_check_anon_fridge_fails_when_short(self):
        result = check_anon_fridge_for_recipe(
            self.recipe,
            [{'ingredient_id': self.chicken.id, 'unit_id': self.g.id, 'quantity': 100}]
        )
        self.assertEqual(result, 'chicken breast')

    def test_subtract_anon_fridge_for_recipe(self):
        request = self._make_request([{'ingredient_id': self.chicken.id, 'unit_id': self.g.id, 'quantity': 300}])
        subtract_anon_fridge_for_recipe(self.recipe, request)
        self.assertAlmostEqual(request.session['anon_fridge'][0]['quantity'], 100, places=2)

    def test_subtract_anon_fridge_removes_entry_when_empty(self):
        request = self._make_request([{'ingredient_id': self.chicken.id, 'unit_id': self.g.id, 'quantity': 200}])
        subtract_anon_fridge_for_recipe(self.recipe, request)
        self.assertEqual(len(request.session['anon_fridge']), 0)


class NutritionCalculationTests(BaseConversionTestCase):

    def test_nutrients_at_base_quantity(self):
        # 100ml milk → 42 kcal
        result = self.milk.get_nutrients_dict(self.milk_ml, 100)
        self.assertAlmostEqual(result['kcal'], 42, places=2)

    def test_nutrients_half_base_quantity(self):
        # 50ml milk → 21 kcal
        result = self.milk.get_nutrients_dict(self.milk_ml, 50)
        self.assertAlmostEqual(result['kcal'], 21, places=2)

    def test_nutrients_with_cup_unit(self):
        # 1 cup = 240ml → 42 * (240/100) = 100.8 kcal
        result = self.milk.get_nutrients_dict(self.milk_cup, 1)
        self.assertAlmostEqual(result['kcal'], 100.8, places=2)

    def test_nutrients_with_tbsp(self):
        # 1 tbsp = 15ml → 42 * (15/100) = 6.3 kcal
        result = self.milk.get_nutrients_dict(self.milk_tbsp, 1)
        self.assertAlmostEqual(result['kcal'], 6.3, places=2)

    def test_nutrients_chicken_oz(self):
        # 1oz = 28.35g → 165 * (28.35/100) kcal
        result = self.chicken.get_nutrients_dict(self.chicken_oz, 1)
        self.assertAlmostEqual(result['kcal'], 165 * 28.35 / 100, places=1)

    def test_recipe_total_nutrients(self):
        # 200g chicken (330 kcal) + 1 cup milk (100.8 kcal) = 430.8 kcal
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.milk, quantity=1, unit=self.milk_cup)
        self.assertAlmostEqual(self.recipe.nutrients['kcal'], 430.8, places=1)

    def test_recipe_kcal_per_serving(self):
        # 200g chicken = 330 kcal, 2 servings → 165 kcal/serving
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.chicken, quantity=200, unit=self.chicken_g)
        self.assertAlmostEqual(self.recipe.kcal_per_serving, 165, places=1)


class TrackerTests(TestCase):

    def test_deficit(self):
        tracker = Tracker(maintenance_calories=2000, name='Test')
        result = tracker.calculate_deficit([1500, 1500])
        self.assertIn('deficit', result.lower())
        self.assertIn('1000', result)

    def test_surplus(self):
        tracker = Tracker(maintenance_calories=2000, name='Test')
        result = tracker.calculate_deficit([2500, 2500])
        self.assertIn('surplus', result.lower())

    def test_perfect_balance(self):
        tracker = Tracker(maintenance_calories=2000, name='Test')
        result = tracker.calculate_deficit([2000, 2000])
        self.assertIn('perfect balance', result.lower())

    def test_kg_calculation(self):
        # 2000 kcal deficit / 7830 = 0.26 kg
        tracker = Tracker(maintenance_calories=2000, name='Test')
        result = tracker.calculate_deficit([0])
        self.assertIn('0.26', result)


class BiometricsCalculationTests(TestCase):

    def test_male_bmr(self):
        data = {'gender': 'M', 'age': 25, 'weight_kg': 70, 'height_cm': 175, 'activity_level': 'sedentary'}
        result = calculate_from_session(data)
        expected = round(10*70 + 6.25*175 - 5*25 + 5, 2)
        self.assertAlmostEqual(result.bmr, expected, places=1)

    def test_female_bmr(self):
        data = {'gender': 'F', 'age': 30, 'weight_kg': 60, 'height_cm': 165, 'activity_level': 'light'}
        result = calculate_from_session(data)
        expected = round(10*60 + 6.25*165 - 5*30 - 161, 2)
        self.assertAlmostEqual(result.bmr, expected, places=1)

    def test_tdee_sedentary(self):
        data = {'gender': 'M', 'age': 25, 'weight_kg': 70, 'height_cm': 175, 'activity_level': 'sedentary'}
        result = calculate_from_session(data)
        expected_bmr = round(10*70 + 6.25*175 - 5*25 + 5, 2)
        self.assertAlmostEqual(result.tdee, round(expected_bmr * 1.2, 2), places=1)

    def test_tdee_very_active(self):
        data = {'gender': 'M', 'age': 25, 'weight_kg': 70, 'height_cm': 175, 'activity_level': 'very'}
        result = calculate_from_session(data)
        expected_bmr = round(10*70 + 6.25*175 - 5*25 + 5, 2)
        self.assertAlmostEqual(result.tdee, round(expected_bmr * 1.725, 2), places=1)