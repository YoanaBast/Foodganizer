import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit
from recipes.models import Recipe, RecipeCategory, RecipeIngredient

User = get_user_model()


class RecipeViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='recipeuser', password='pass', email='r@r.com')
        self.other = User.objects.create_user(username='other', password='pass', email='o@o.com')

        self.g = MeasurementUnit.objects.create(code='g', name_singular='gram', name_plural='grams')
        self.ingredient = Ingredient.objects.create(
            name='test ingredient', base_quantity=100, default_unit=self.g,
            base_quantity_kcal=100, base_quantity_protein=10,
            base_quantity_carbs=10, base_quantity_fat=5,
            created_by=self.user, updated_by=self.user,
        )
        self.imu = IngredientMeasurementUnit.objects.create(
            ingredient=self.ingredient, unit=self.g, conversion_to_base=1
        )
        self.recipe = Recipe.objects.create(
            name='test recipe', instructions='do stuff', servings=2,
            created_by=self.user, updated_by=self.user,
        )

    # --- ManageRecipesView ---

    def test_manage_recipes_get(self):
        response = self.client.get(reverse('manage_recipes'))
        self.assertEqual(response.status_code, 200)

    def test_manage_recipes_contains_recipe(self):
        response = self.client.get(reverse('manage_recipes'))
        self.assertContains(response, 'test recipe')

    def test_manage_recipes_search(self):
        Recipe.objects.create(name='chicken soup', instructions='cook', servings=2,
                               created_by=self.user, updated_by=self.user)
        response = self.client.get(reverse('manage_recipes'), {'search': 'chicken'})
        self.assertContains(response, 'chicken soup')
        self.assertNotContains(response, 'test recipe')

    # --- RecipeDetailView ---

    def test_recipe_detail_get(self):
        response = self.client.get(reverse('recipe_detail', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test recipe')

    def test_recipe_detail_404(self):
        response = self.client.get(reverse('recipe_detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    # --- AddRecipeView ---

    def test_add_recipe_requires_login(self):
        response = self.client.get(reverse('add_recipe'))
        self.assertRedirects(response, f'/users/login/?next={reverse("add_recipe")}')

    def test_add_recipe_get_authenticated(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.get(reverse('add_recipe'))
        self.assertEqual(response.status_code, 200)

    # --- DeleteRecipeView ---

    def test_delete_recipe_requires_login(self):
        response = self.client.post(reverse('delete_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertRedirects(response, f'/users/login/?next={reverse("delete_recipe", kwargs={"pk": self.recipe.pk})}')

    def test_delete_recipe_owner_can_delete(self):
        self.client.login(username='recipeuser', password='pass')
        self.client.post(reverse('delete_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertFalse(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_delete_recipe_other_user_denied(self):
        self.client.login(username='other', password='pass')
        response = self.client.post(reverse('delete_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk).exists())

    # --- EditRecipeView ---

    def test_edit_recipe_requires_login(self):
        response = self.client.get(reverse('edit_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertRedirects(response, f'/users/login/?next={reverse("edit_recipe", kwargs={"pk": self.recipe.pk})}')

    def test_edit_recipe_get_authenticated(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.get(reverse('edit_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)

    def test_edit_recipe_other_user_denied(self):
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('edit_recipe', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 403)

    # --- toggle_favourite ---

    def test_toggle_favourite_adds(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(reverse('toggle_favourite', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['favourited'])

    def test_toggle_favourite_removes(self):
        self.recipe.favourited_by.add(self.user)
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(reverse('toggle_favourite', kwargs={'pk': self.recipe.pk}))
        self.assertFalse(json.loads(response.content)['favourited'])

    def test_toggle_favourite_requires_login(self):
        response = self.client.post(reverse('toggle_favourite', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 302)

    def test_toggle_favourite_get_not_allowed(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.get(reverse('toggle_favourite', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 405)

    # --- add_recipe_category_ajax ---

    def test_add_recipe_category_valid(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(
            reverse('add_recipe_category_ajax'),
            data=json.dumps({'name': 'desserts'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RecipeCategory.objects.filter(name='desserts').exists())

    def test_add_recipe_category_duplicate(self):
        RecipeCategory.objects.create(name='soups')
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(
            reverse('add_recipe_category_ajax'),
            data=json.dumps({'name': 'soups'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_add_recipe_category_empty_name(self):
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(
            reverse('add_recipe_category_ajax'),
            data=json.dumps({'name': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    # --- delete_category_ajax ---

    def test_delete_recipe_category_owner_can_delete(self):
        cat = RecipeCategory.objects.create(name='to delete', created_by=self.user)
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(reverse('delete_recipe_category_ajax', kwargs={'pk': cat.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RecipeCategory.objects.filter(pk=cat.pk).exists())

    def test_delete_recipe_category_other_user_denied(self):
        cat = RecipeCategory.objects.create(name='protected', created_by=self.other)
        self.client.login(username='recipeuser', password='pass')
        response = self.client.post(reverse('delete_recipe_category_ajax', kwargs={'pk': cat.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RecipeCategory.objects.filter(pk=cat.pk).exists())