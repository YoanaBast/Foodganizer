from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from ingredients.models import Ingredient, IngredientCategory, MeasurementUnit, IngredientMeasurementUnit
from recipes.models import Recipe, RecipeIngredient

User = get_user_model()


class BaseAPITestCase(APITestCase):
    """
    Base class — creates users and helper methods shared across all test cases.
    """

    def setUp(self):
        # Regular user (owner)
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@test.com')

        # Another regular user (non-owner)
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123', email='other@test.com')

        # Moderator user
        self.moderator = User.objects.create_user(username='moderator', password='testpass123', email='mod@test.com')
        mod_group, _ = Group.objects.get_or_create(name='Moderator')
        self.moderator.groups.add(mod_group)

        # Shared test data
        self.category = IngredientCategory.objects.create(name='test category')
        self.unit = MeasurementUnit.objects.create(code='g', name_singular='gram', name_plural='grams')
        self.ingredient = Ingredient.objects.create(
            name='test ingredient',
            base_quantity=100,
            default_unit=self.unit,
            category=self.category,
            created_by=self.user,
            updated_by=self.user,
        )
        IngredientMeasurementUnit.objects.create(
            ingredient=self.ingredient,
            unit=self.unit,
            conversion_to_base=1,
        )
        self.recipe = Recipe.objects.create(
            name='test recipe',
            instructions='Test instructions',
            servings=2,
            created_by=self.user,
            updated_by=self.user,
        )

    def get_token(self, user):
        """Helper: returns Authorization header for a given user."""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def auth(self, user=None):
        """Shortcut: authenticate as user (default: self.user)."""
        return self.get_token(user or self.user)


# ---------------------------------------------------------------------------
# TOKEN TESTS
# ---------------------------------------------------------------------------

class TokenTests(BaseAPITestCase):

    def test_obtain_token_valid_credentials(self):
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_obtain_token_invalid_credentials(self):
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post('/api/token/refresh/', {
            'refresh': str(refresh),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


# ---------------------------------------------------------------------------
# INGREDIENT TESTS
# ---------------------------------------------------------------------------

class IngredientListCreateTests(BaseAPITestCase):

    def test_list_ingredients_anonymous(self):
        """Anyone can list ingredients."""
        response = self.client.get('/api/ingredients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_ingredients_returns_correct_data(self):
        response = self.client.get('/api/ingredients/')
        names = [i['name'] for i in response.data]
        self.assertIn('test ingredient', names)

    def test_create_ingredient_authenticated(self):
        """Authenticated user can create an ingredient."""
        response = self.client.post('/api/ingredients/', {
            'name': 'broccoli',
            'base_quantity': 100,
            'default_unit_code': 'g',
            'category_name': 'vegetables',
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'broccoli')

    def test_create_ingredient_anonymous_forbidden(self):
        """Anonymous user cannot create an ingredient."""
        response = self.client.post('/api/ingredients/', {
            'name': 'spinach',
            'base_quantity': 100,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_ingredient_get_or_create(self):
        """POSTing an existing ingredient name returns the existing one, not a duplicate."""
        response1 = self.client.post('/api/ingredients/', {
            'name': 'test ingredient',
            'base_quantity': 100,
            'default_unit_code': 'g',
        }, format='json', **self.auth())
        response2 = self.client.post('/api/ingredients/', {
            'name': 'test ingredient',
            'base_quantity': 100,
            'default_unit_code': 'g',
        }, format='json', **self.auth())
        self.assertEqual(response1.data['id'], response2.data['id'])

    def test_ingredient_response_includes_nutrients(self):
        response = self.client.get('/api/ingredients/')
        first = response.data[0]
        self.assertIn('nutrients', first)


class IngredientDetailTests(BaseAPITestCase):

    def test_retrieve_ingredient_anonymous(self):
        """Anyone can retrieve ingredient detail."""
        response = self.client.get(f'/api/ingredients/{self.ingredient.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test ingredient')

    def test_update_ingredient_as_owner(self):
        """Owner can update their ingredient."""
        response = self.client.patch(f'/api/ingredients/{self.ingredient.id}/', {
            'base_quantity': 200,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['base_quantity'], 200.0)

    def test_update_ingredient_as_moderator(self):
        """Moderator can update any ingredient."""
        response = self.client.patch(f'/api/ingredients/{self.ingredient.id}/', {
            'base_quantity': 150,
        }, format='json', **self.auth(self.moderator))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_ingredient_as_non_owner_forbidden(self):
        """Non-owner, non-moderator cannot update."""
        response = self.client.patch(f'/api/ingredients/{self.ingredient.id}/', {
            'base_quantity': 999,
        }, format='json', **self.auth(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_ingredient_as_owner(self):
        """Owner can delete their ingredient."""
        response = self.client.delete(f'/api/ingredients/{self.ingredient.id}/', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_ingredient_as_non_owner_forbidden(self):
        """Non-owner cannot delete."""
        response = self.client.delete(f'/api/ingredients/{self.ingredient.id}/', **self.auth(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_ingredient_anonymous_forbidden(self):
        """Anonymous user cannot delete."""
        response = self.client.delete(f'/api/ingredients/{self.ingredient.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# RECIPE TESTS
# ---------------------------------------------------------------------------

class RecipeListCreateTests(BaseAPITestCase):

    def test_list_recipes_anonymous(self):
        """Anyone can list recipes."""
        response = self.client.get('/api/recipes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_recipes_includes_nested_ingredients(self):
        response = self.client.get('/api/recipes/')
        self.assertIn('recipe_ingredient', response.data[0])

    def test_create_recipe_authenticated(self):
        """Authenticated user can create a recipe with nested ingredients."""
        response = self.client.post('/api/recipes/', {
            'name': 'new salad',
            'instructions': 'Mix everything.',
            'servings': 2,
            'category_name': 'salads',
            'ingredients': [
                {'ingredient_name': 'test ingredient', 'quantity': 100, 'unit_code': 'g'}
            ]
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'new salad')

    def test_create_recipe_anonymous_forbidden(self):
        """Anonymous user cannot create a recipe."""
        response = self.client.post('/api/recipes/', {
            'name': 'anonymous recipe',
            'instructions': 'Nope.',
            'servings': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_recipe_get_or_create(self):
        """POSTing a recipe with an existing name returns the existing one."""
        data = {
            'name': 'test recipe',
            'instructions': 'Test instructions',
            'servings': 2,
        }
        response1 = self.client.post('/api/recipes/', data, format='json', **self.auth())
        response2 = self.client.post('/api/recipes/', data, format='json', **self.auth())
        self.assertEqual(response1.data['id'], response2.data['id'])

    def test_create_recipe_creates_ingredient_if_not_exists(self):
        """Posting a recipe with a new ingredient creates that ingredient automatically."""
        response = self.client.post('/api/recipes/', {
            'name': 'brand new recipe',
            'instructions': 'Cook it.',
            'servings': 1,
            'ingredients': [
                {'ingredient_name': 'totally new ingredient', 'quantity': 50, 'unit_code': 'g'}
            ]
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Ingredient.objects.filter(name='totally new ingredient').exists())


# ---------------------------------------------------------------------------
# INGREDIENT MEASUREMENT UNIT TESTS
# ---------------------------------------------------------------------------

class IngredientMeasurementUnitTests(BaseAPITestCase):

    def test_add_unit_to_ingredient_as_owner(self):
        """Owner can add a measurement unit to their ingredient."""
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'cup',
            'unit_name_singular': 'cup',
            'unit_name_plural': 'cups',
            'conversion_to_base': 240,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['unit_code'], 'cup')
        self.assertEqual(response.data['conversion_to_base'], 240)

    def test_add_unit_creates_measurement_unit_if_not_exists(self):
        """Posting a new unit_code creates the MeasurementUnit automatically."""
        from ingredients.models import MeasurementUnit
        self.assertFalse(MeasurementUnit.objects.filter(code='tbsp').exists())
        self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'tbsp',
            'conversion_to_base': 15,
        }, format='json', **self.auth(self.user))
        self.assertTrue(MeasurementUnit.objects.filter(code='tbsp').exists())

    def test_add_unit_updates_conversion_if_already_linked(self):
        """Adding a unit that is already linked updates the conversion_to_base."""
        # first add
        self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'cup',
            'conversion_to_base': 240,
        }, format='json', **self.auth(self.user))
        # update with different conversion
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'cup',
            'conversion_to_base': 250,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['conversion_to_base'], 250)

    def test_add_unit_as_moderator(self):
        """Moderator can add units to any ingredient."""
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'oz',
            'conversion_to_base': 28.35,
        }, format='json', **self.auth(self.moderator))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_unit_as_non_owner_forbidden(self):
        """Non-owner, non-moderator cannot add units."""
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'lb',
            'conversion_to_base': 453,
        }, format='json', **self.auth(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_unit_anonymous_forbidden(self):
        """Anonymous user cannot add units."""
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'kg',
            'conversion_to_base': 1000,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_unit_invalid_conversion(self):
        """Conversion below 0.01 should fail validation."""
        response = self.client.post(f'/api/ingredients/{self.ingredient.id}/units/', {
            'unit_code': 'mg',
            'conversion_to_base': 0,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_unit_nonexistent_ingredient(self):
        """Adding a unit to a non-existent ingredient returns 404."""
        response = self.client.post('/api/ingredients/99999/units/', {
            'unit_code': 'g',
            'conversion_to_base': 1,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# GET OR CREATE EDGE CASE TESTS
# ---------------------------------------------------------------------------

class GetOrCreateTests(BaseAPITestCase):

    def test_create_ingredient_with_nonexistent_category_creates_it(self):
        """Passing a new category_name creates the category automatically."""
        from ingredients.models import IngredientCategory
        self.assertFalse(IngredientCategory.objects.filter(name='superfoods').exists())
        response = self.client.post('/api/ingredients/', {
            'name': 'chia seeds',
            'base_quantity': 100,
            'default_unit_code': 'g',
            'category_name': 'superfoods',
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(IngredientCategory.objects.filter(name='superfoods').exists())

    def test_create_ingredient_with_nonexistent_unit_creates_it(self):
        """Passing a new default_unit_code creates the MeasurementUnit automatically."""
        from ingredients.models import MeasurementUnit
        self.assertFalse(MeasurementUnit.objects.filter(code='tsp').exists())
        response = self.client.post('/api/ingredients/', {
            'name': 'salt',
            'base_quantity': 100,
            'default_unit_code': 'tsp',
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MeasurementUnit.objects.filter(code='tsp').exists())

    def test_create_ingredient_with_nonexistent_tags_creates_them(self):
        """Passing new dietary_tag_names creates those tags automatically."""
        from ingredients.models import IngredientDietaryTag
        self.assertFalse(IngredientDietaryTag.objects.filter(name='keto').exists())
        response = self.client.post('/api/ingredients/', {
            'name': 'avocado',
            'base_quantity': 100,
            'default_unit_code': 'g',
            'dietary_tag_names': ['keto', 'vegan'],
        }, format='json', **self.auth())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(IngredientDietaryTag.objects.filter(name='keto').exists())
        self.assertTrue(IngredientDietaryTag.objects.filter(name='vegan').exists())


class RecipeDetailTests(BaseAPITestCase):

    def test_retrieve_recipe_anonymous(self):
        """Anyone can retrieve recipe detail."""
        response = self.client.get(f'/api/recipes/{self.recipe.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test recipe')

    def test_retrieve_recipe_includes_nutrients(self):
        response = self.client.get(f'/api/recipes/{self.recipe.id}/')
        self.assertIn('nutrients', response.data)
        self.assertIn('nutrients_per_serving', response.data)

    def test_update_recipe_as_owner(self):
        """Owner can update their recipe."""
        response = self.client.patch(f'/api/recipes/{self.recipe.id}/', {
            'servings': 4,
        }, format='json', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['servings'], 4)

    def test_update_recipe_as_moderator(self):
        """Moderator can update any recipe."""
        response = self.client.patch(f'/api/recipes/{self.recipe.id}/', {
            'servings': 6,
        }, format='json', **self.auth(self.moderator))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_recipe_as_non_owner_forbidden(self):
        """Non-owner, non-moderator cannot update."""
        response = self.client.patch(f'/api/recipes/{self.recipe.id}/', {
            'servings': 99,
        }, format='json', **self.auth(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_recipe_as_owner(self):
        """Owner can delete their recipe."""
        response = self.client.delete(f'/api/recipes/{self.recipe.id}/', **self.auth(self.user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_recipe_as_non_owner_forbidden(self):
        """Non-owner cannot delete."""
        response = self.client.delete(f'/api/recipes/{self.recipe.id}/', **self.auth(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_recipe_anonymous_forbidden(self):
        """Anonymous user cannot delete."""
        response = self.client.delete(f'/api/recipes/{self.recipe.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)