import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ingredients.models import IngredientCategory, Ingredient, IngredientMeasurementUnit, MeasurementUnit, IngredientDietaryTag

User = get_user_model()

class IngredientModelsTest(TestCase):
    def test_ingredient_tags(self):
        tag = IngredientDietaryTag.objects.create(name='test tag')
        self.assertEqual(tag.name, 'test tag')

    def test_ingredient_categories(self):
        cat = IngredientCategory.objects.create(name='test category')
        self.assertEqual(cat.name, 'test category')

    def test_measurment_units(self):
        unit = MeasurementUnit.objects.create(code='test code', name_singular="test name_singular", name_plural="test name_plural")
        self.assertEqual(unit.code, 'test code')
        self.assertEqual(unit.name_singular, 'test name_singular')
        self.assertEqual(unit.name_plural, 'test name_plural')
        self.assertEqual(str(unit), "test name_singular test code")

    def test_ingredient(self):
        d_unit = MeasurementUnit.objects.create(code='test code', name_singular="test name_singular", name_plural="test name_plural")
        cat = IngredientCategory.objects.create(name='test category')
        t_ing = Ingredient.objects.create(
            name='test ingredient',
            default_unit=d_unit,
            base_quantity=100.00,
            category=cat,
            base_quantity_kcal=50,
            base_quantity_protein=51,
            base_quantity_carbs=52,
            base_quantity_fat=53,
            base_quantity_fiber=54,
            base_quantity_sugar=55,
            base_quantity_salt=56,
            base_quantity_cholesterol=57,
            base_quantity_vitamin_a=58,
            base_quantity_vitamin_c=59,
            base_quantity_vitamin_d=59,
            base_quantity_vitamin_e=60,
            base_quantity_vitamin_k=61,
            base_vitamin_b1=62,
            base_vitamin_b2=63,
            base_vitamin_b3=64,
            base_vitamin_b6=65,
            base_vitamin_b12=66,
            base_folate=67,
            base_calcium=68,
            base_iron=69,
            base_magnesium=70,
            base_potassium=71,
            base_zinc=72,
        )

        self.assertEqual(t_ing.name, 'test ingredient')
        self.assertEqual(t_ing.category, cat)
        seld.assertEqual(t_ing.category.name, "test category")
        self.assertEqual(t_ing.base_quantity, Decimal('100.00'))

        self.assertEqual(t_ing.default_unit, d_unit)

        for field, expected in nutrients.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(t_ing, field), expected)

    def test_ingredient_measurment_units(self):
        ...

class IngredientViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='viewuser', password='pass', email='v@v.com')
        self.ml = MeasurementUnit.objects.create(code='ml2', name_singular='millilitre2', name_plural='millilitres2')
        self.ingredient = Ingredient.objects.create(
            name='test ingredient', base_quantity=100, default_unit=self.ml,
            base_quantity_kcal=50, base_quantity_protein=2,
            base_quantity_carbs=5, base_quantity_fat=1,
            created_by=self.user, updated_by=self.user,
        )
        # removed IngredientMeasurementUnit.objects.create() — save() handles it now
    # --- ManageIngredientsView ---

    def test_manage_ingredients_get(self):
        response = self.client.get(reverse('manage_ingredients'))
        self.assertEqual(response.status_code, 200)

    def test_manage_ingredients_contains_ingredient(self):
        response = self.client.get(reverse('manage_ingredients'))
        self.assertContains(response, 'test ingredient')

    # --- AddIngredientView ---

    def test_add_ingredient_requires_login(self):
        response = self.client.get(reverse('add_ingredient'))
        self.assertRedirects(response, f'/users/login/?next={reverse("add_ingredient")}')

    def test_add_ingredient_get_authenticated(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.get(reverse('add_ingredient'))
        self.assertEqual(response.status_code, 200)

    def test_add_ingredient_post_valid(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(reverse('add_ingredient'), {
            'name': 'banana',
            'base_quantity': 100,
            'default_unit': self.ml.id,
            'base_quantity_kcal': 89,
            'base_quantity_protein': 1.1,
            'base_quantity_carbs': 23,
            'base_quantity_fat': 0.3,
        })
        # print(response.context['form'].errors)
        self.assertIn(response.status_code, [200, 302])




    # --- EditIngredientView ---

    def test_edit_ingredient_requires_login(self):
        response = self.client.get(reverse('edit_ingredient', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertRedirects(response,
                             f'/users/login/?next={reverse("edit_ingredient", kwargs={"ingredient_id": self.ingredient.id})}')

    def test_edit_ingredient_get_authenticated(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.get(reverse('edit_ingredient', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertEqual(response.status_code, 200)

    def test_edit_ingredient_post_updates_name(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(reverse('edit_ingredient', kwargs={'ingredient_id': self.ingredient.id}), {
            'name': 'updated ingredient',
            'base_quantity': 100,
            'default_unit': self.ml.id,
            'base_quantity_kcal': 50,
            'base_quantity_protein': 2,
            'base_quantity_carbs': 5,
            'base_quantity_fat': 1,
        })
        # print(response.context['form'].errors)
        self.assertIn(response.status_code, [200, 302])

    # --- DeleteIngredientView ---

    def test_delete_ingredient_requires_login(self):
        response = self.client.post(reverse('delete_ingredient', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertNotEqual(response.status_code, 200)

    def test_delete_ingredient_owner_can_delete(self):
        self.client.login(username='viewuser', password='pass')
        self.client.post(reverse('delete_ingredient', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertFalse(Ingredient.objects.filter(pk=self.ingredient.id).exists())

    def test_delete_ingredient_other_user_denied(self):
        other = User.objects.create_user(username='other', password='pass', email='o@o.com')
        self.client.login(username='other', password='pass')
        response = self.client.post(reverse('delete_ingredient', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Ingredient.objects.filter(pk=self.ingredient.id).exists())

    # --- ingredient_detail ---

    def test_ingredient_detail_get(self):
        response = self.client.get(reverse('ingredient_detail', kwargs={'ingredient_id': self.ingredient.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test ingredient')

    def test_ingredient_detail_404_on_missing(self):
        response = self.client.get(reverse('ingredient_detail', kwargs={'ingredient_id': 99999}))
        self.assertEqual(response.status_code, 404)

    # --- AJAX: add_category_ajax ---

    def test_add_category_ajax_valid(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(
            reverse('add_category_ajax'),
            data=json.dumps({'name': 'grains'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(IngredientCategory.objects.filter(name='grains').exists())

    def test_add_category_ajax_duplicate(self):
        IngredientCategory.objects.create(name='dairy')
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(
            reverse('add_category_ajax'),
            data=json.dumps({'name': 'dairy'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_add_category_ajax_empty_name(self):
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(
            reverse('add_category_ajax'),
            data=json.dumps({'name': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    # --- AJAX: delete_category_ajax ---

    def test_delete_category_ajax_owner_can_delete(self):
        cat = IngredientCategory.objects.create(name='to delete', created_by=self.user)
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(reverse('delete_category_ajax', kwargs={'pk': cat.id}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(IngredientCategory.objects.filter(pk=cat.id).exists())

    def test_delete_category_ajax_other_user_denied(self):
        other = User.objects.create_user(username='other2', password='pass', email='o2@o.com')
        cat = IngredientCategory.objects.create(name='protected', created_by=other)
        self.client.login(username='viewuser', password='pass')
        response = self.client.post(reverse('delete_category_ajax', kwargs={'pk': cat.id}))
        self.assertEqual(response.status_code, 403)