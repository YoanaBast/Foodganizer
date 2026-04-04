from rest_framework import status
from rest_framework.permissions import SAFE_METHODS, BasePermission, AllowAny
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from ingredients.models import Ingredient
from recipes.models import Recipe
from .mixins import IsOwnerOrModeratorOrReadOnly, ReadWriteSerializerMixin
from .serializers import (
    IngredientSerializer,
    IngredientMeasurementUnitSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
)



# ---------------------------------------------------------------------------
# INGREDIENT VIEWS
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# RECIPE VIEWS
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# INGREDIENT MEASUREMENT UNIT VIEW
# ---------------------------------------------------------------------------

class AddIngredientMeasurementUnitApiView(APIView):
    """
    POST /api/ingredients/<id>/units/
    Add (or update) a measurement unit for an ingredient.
    Only the ingredient owner or a moderator can do this.

    Payload:
    {
        "unit_code": "cup",
        "unit_name_singular": "cup",
        "unit_name_plural": "cups",
        "conversion_to_base": 240
    }

    get_or_create logic:
    - MeasurementUnit: found or created by unit_code
    - IngredientMeasurementUnit: found or created by ingredient+unit
    - If already linked: conversion_to_base is updated
    """
    permission_classes = [IsOwnerOrModeratorOrReadOnly]

    def get_ingredient(self, pk):
        try:
            return Ingredient.objects.get(pk=pk)
        except Ingredient.DoesNotExist:
            return None

    def post(self, request, pk):
        ingredient = self.get_ingredient(pk)
        if not ingredient:
            return Response({'error': 'Ingredient not found.'}, status=status.HTTP_404_NOT_FOUND)

        # manual object-level permission check (APIView doesn't call has_object_permission automatically)
        self.check_object_permissions(request, ingredient)

        serializer = IngredientMeasurementUnitSerializer(data=request.data)
        if serializer.is_valid():
            imu = serializer.save(ingredient=ingredient)
            return Response({
                'ingredient': ingredient.name,
                'unit_code': imu.unit.code,
                'unit_name_singular': imu.unit.name_singular,
                'unit_name_plural': imu.unit.name_plural,
                'conversion_to_base': imu.conversion_to_base,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)