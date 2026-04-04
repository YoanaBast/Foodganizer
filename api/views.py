from django.shortcuts import render

from rest_framework.permissions import SAFE_METHODS, BasePermission, AllowAny
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from ingredients.models import Ingredient
from recipes.models import Recipe
from .mixins import ReadWriteSerializerMixin
from .serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
)

# Create your views here.

"""
PERMISSION
"""

class IsOwnerOrModeratorOrReadOnly(BasePermission):
    """
    - Safe methods (GET, HEAD, OPTIONS): open to everyone, even anonymous.
    - Unsafe methods (POST, PUT, PATCH, DELETE):
        - POST (create): any authenticated user.
        - PUT/PATCH/DELETE: only the owner or a Moderator group member.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        # ALL unsafe methods (POST, PUT, PATCH, DELETE) require login
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        is_moderator = request.user.groups.filter(name='Moderator').exists()
        is_owner = getattr(obj, 'created_by', None) == request.user
        return is_owner or is_moderator




"""
INGREDIENT VIEWS
"""
class ListCreateIngredientApiView(ListCreateAPIView):
    """
    GET  /api/ingredients/  → list all ingredients (anyone)
    POST /api/ingredients/  → create ingredient (authenticated users)

    get_or_create is handled inside IngredientSerializer.create()
    so POSTing an ingredient that already exists returns the existing one
    without raising a duplicate error.
    """
    permission_classes = [IsOwnerOrModeratorOrReadOnly]
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.select_related(
        'category', 'default_unit'
    ).prefetch_related(
        'dietary_tag', 'measurement_units__unit'
    ).all().order_by('name')


class RetrieveUpdateDestroyIngredientApiView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/ingredients/<id>/  → detail (anyone)
    PUT    /api/ingredients/<id>/  → full update (owner or moderator)
    PATCH  /api/ingredients/<id>/  → partial update (owner or moderator)
    DELETE /api/ingredients/<id>/  → delete (owner or moderator)
    """
    permission_classes = [IsOwnerOrModeratorOrReadOnly]
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.select_related(
        'category', 'default_unit'
    ).prefetch_related(
        'dietary_tag', 'measurement_units__unit'
    ).all()


"""
RECIPE VIEWS
"""

class ListCreateRecipeApiView(ReadWriteSerializerMixin, ListCreateAPIView):
    """
    GET  /api/recipes/  → list all recipes with nested ingredients (anyone)
    POST /api/recipes/  → create recipe + ingredients in one request (authenticated)

    Example POST body:
    {
        "name": "Grilled Chicken Salad",
        "instructions": "Grill the chicken, mix with lettuce...",
        "servings": 2,
        "category_name": "salads",
        "ingredients": [
            {"ingredient_name": "chicken breast", "quantity": 200, "unit_code": "g"},
            {"ingredient_name": "lettuce",         "quantity": 100, "unit_code": "g"}
        ]
    }

    If the recipe name already exists, the existing recipe is returned (get_or_create).
    Same for each ingredient and measurement unit inside the list.
    """
    permission_classes = [IsOwnerOrModeratorOrReadOnly]
    read_serializer = RecipeReadSerializer
    write_serializer = RecipeWriteSerializer
    queryset = Recipe.objects.select_related('category', 'created_by').prefetch_related(
        'recipe_ingredient__ingredient__dietary_tag',
        'recipe_ingredient__ingredient__category',
        'recipe_ingredient__ingredient__default_unit',
        'recipe_ingredient__unit__unit',
    ).all().order_by('name')


class RetrieveUpdateDestroyRecipeApiView(ReadWriteSerializerMixin, RetrieveUpdateDestroyAPIView):
    """
    GET    /api/recipes/<id>/  → full recipe detail (anyone)
    PUT    /api/recipes/<id>/  → update recipe + sync ingredients (owner or moderator)
    PATCH  /api/recipes/<id>/  → partial update (owner or moderator)
    DELETE /api/recipes/<id>/  → delete (owner or moderator)

    Note on ingredient sync during update:
    _sync_ingredients() is non-destructive — it only adds or updates ingredients
    that are in the payload. Existing recipe ingredients NOT in the payload are
    left untouched. If you want full replacement, clear recipe_ingredient first.
    """
    permission_classes = [IsOwnerOrModeratorOrReadOnly]
    read_serializer = RecipeReadSerializer
    write_serializer = RecipeWriteSerializer
    queryset = Recipe.objects.select_related('category', 'created_by').prefetch_related(
        'recipe_ingredient__ingredient__dietary_tag',
        'recipe_ingredient__ingredient__category',
        'recipe_ingredient__ingredient__default_unit',
        'recipe_ingredient__unit__unit',
    ).all()