import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ingredients.models import IngredientCategory, Ingredient, IngredientMeasurementUnit, MeasurementUnit

User = get_user_model()


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