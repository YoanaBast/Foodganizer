from rest_framework import serializers

from ingredients.models import (
    Ingredient, IngredientCategory, IngredientDietaryTag,
    MeasurementUnit, IngredientMeasurementUnit,
)
from recipes.models import Recipe, RecipeIngredient, RecipeCategory


# ---------------------------------------------------------------------------
# INGREDIENT SERIALIZERS
# ---------------------------------------------------------------------------

class MeasurementUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementUnit
        fields = ('id', 'code', 'name_singular', 'name_plural')


class IngredientCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientCategory
        fields = ('id', 'name')


class IngredientDietaryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientDietaryTag
        fields = ('id', 'name')


class IngredientSerializer(serializers.ModelSerializer):
    """
    Flat serializer used for:
    - GET /ingredients/        (list)
    - GET /ingredients/<id>/   (detail)
    - POST /ingredients/       (create)
    - PUT/PATCH /ingredients/<id>/

    category and dietary_tag support get_or_create:
      - Pass {'name': 'vegetables'} → finds or creates it
      - Pass an int id → looks it up
    """
    category = IngredientCategorySerializer(read_only=True)
    dietary_tag = IngredientDietaryTagSerializer(many=True, read_only=True)
    default_unit = MeasurementUnitSerializer(read_only=True)
    nutrients = serializers.SerializerMethodField()

    # Write-only fields for get_or_create on related objects
    category_name = serializers.CharField(write_only=True, required=False, allow_null=True)
    default_unit_code = serializers.CharField(write_only=True, required=False, allow_null=True)
    dietary_tag_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Ingredient
        fields = (
            'id', 'name', 'base_quantity',
            'category', 'category_name',
            'dietary_tag', 'dietary_tag_names',
            'default_unit', 'default_unit_code',
            'nutrients',
        )
        extra_kwargs = {
            'name': {'validators': []},  # disable unique validator, get_or_create handles it
        }

    def get_nutrients(self, obj):
        return obj.nutrients_with_units

    def _resolve_category(self, name):
        if not name:
            return None
        obj, _ = IngredientCategory.objects.get_or_create(name=name.strip().lower())
        return obj

    def _resolve_default_unit(self, code):
        if not code:
            return None
        obj, _ = MeasurementUnit.objects.get_or_create(
            code=code.strip().lower(),
            defaults={'name_singular': code, 'name_plural': code}
        )
        return obj

    def _resolve_dietary_tags(self, names):
        tags = []
        for name in names:
            tag, _ = IngredientDietaryTag.objects.get_or_create(name=name.strip().lower())
            tags.append(tag)
        return tags

    def create(self, validated_data):
        category_name = validated_data.pop('category_name', None)
        default_unit_code = validated_data.pop('default_unit_code', None)
        dietary_tag_names = validated_data.pop('dietary_tag_names', [])

        validated_data['category'] = self._resolve_category(category_name)
        validated_data['default_unit'] = self._resolve_default_unit(default_unit_code)

        # set created_by from context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user

        ingredient, _ = Ingredient.objects.get_or_create(
            name=validated_data.pop('name').strip().lower(),
            defaults=validated_data,
        )

        if dietary_tag_names:
            tags = self._resolve_dietary_tags(dietary_tag_names)
            ingredient.dietary_tag.set(tags)

        # Auto-create IngredientMeasurementUnit for default_unit
        if ingredient.default_unit:
            IngredientMeasurementUnit.objects.get_or_create(
                ingredient=ingredient,
                unit=ingredient.default_unit,
                defaults={'conversion_to_base': 1}
            )

        return ingredient

    def update(self, instance, validated_data):
        category_name = validated_data.pop('category_name', None)
        default_unit_code = validated_data.pop('default_unit_code', None)
        dietary_tag_names = validated_data.pop('dietary_tag_names', None)

        if category_name is not None:
            instance.category = self._resolve_category(category_name)
        if default_unit_code is not None:
            instance.default_unit = self._resolve_default_unit(default_unit_code)
        if dietary_tag_names is not None:
            tags = self._resolve_dietary_tags(dietary_tag_names)
            instance.dietary_tag.set(tags)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            instance.updated_by = request.user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


# ---------------------------------------------------------------------------
# RECIPE SERIALIZERS
# ---------------------------------------------------------------------------

class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """
    Used inside RecipeReadSerializer — shows the full ingredient + quantity + unit.
    """
    ingredient = IngredientSerializer(read_only=True)
    unit = serializers.SerializerMethodField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'ingredient', 'quantity', 'unit')

    def get_unit(self, obj):
        if obj.unit:
            return {
                'id': obj.unit.id,
                'code': obj.unit.unit.code,
                'name': obj.unit.name_for_quantity(obj.quantity),
            }
        return None


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """
    Handles a single ingredient entry inside a recipe create/update payload.

    Payload example:
    {
        "ingredient_name": "chicken breast",
        "quantity": 200,
        "unit_code": "g",
        "category_name": "meat",          # optional
        "dietary_tag_names": ["high-protein"]  # optional
    }

    get_or_create logic:
    - Ingredient: matched by name (lowercased)
    - MeasurementUnit: matched by code
    - IngredientMeasurementUnit: matched by ingredient + unit
    """
    ingredient_name = serializers.CharField()
    quantity = serializers.FloatField(min_value=0.01)
    unit_code = serializers.CharField()
    category_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dietary_tag_names = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    def _resolve_ingredient(self, name, category_name, dietary_tag_names, request):
        category = None
        if category_name:
            category, _ = IngredientCategory.objects.get_or_create(name=category_name.strip().lower())

        defaults = {'category': category}
        if request and request.user.is_authenticated:
            defaults['created_by'] = request.user
            defaults['updated_by'] = request.user

        ingredient, _ = Ingredient.objects.get_or_create(
            name=name.strip().lower(),
            defaults=defaults,
        )

        for tag_name in dietary_tag_names:
            tag, _ = IngredientDietaryTag.objects.get_or_create(name=tag_name.strip().lower())
            ingredient.dietary_tag.add(tag)

        return ingredient

    def _resolve_unit(self, ingredient, unit_code):
        unit, _ = MeasurementUnit.objects.get_or_create(
            code=unit_code.strip().lower(),
            defaults={
                'name_singular': unit_code,
                'name_plural': unit_code,
            }
        )
        imu, _ = IngredientMeasurementUnit.objects.get_or_create(
            ingredient=ingredient,
            unit=unit,
            defaults={'conversion_to_base': 1}
        )
        return imu

    def to_internal_value(self, data):
        result = super().to_internal_value(data)
        request = self.context.get('request')
        ingredient = self._resolve_ingredient(
            name=result['ingredient_name'],
            category_name=result.get('category_name'),
            dietary_tag_names=result.get('dietary_tag_names', []),
            request=request,
        )
        imu = self._resolve_unit(ingredient, result['unit_code'])
        result['ingredient'] = ingredient
        result['imu'] = imu
        return result


class RecipeReadSerializer(serializers.ModelSerializer):
    """
    Full recipe with nested ingredients + quantities.
    Used for GET requests.
    """
    recipe_ingredient = RecipeIngredientReadSerializer(many=True, read_only=True)
    category = serializers.StringRelatedField()
    nutrients = serializers.SerializerMethodField()
    nutrients_per_serving = serializers.SerializerMethodField()
    cooking_duration = serializers.CharField(read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'instructions', 'servings', 'cooking_duration',
            'category', 'recipe_ingredient',
            'nutrients', 'nutrients_per_serving',
            'created_by',
        )

    def get_nutrients(self, obj):
        return obj.nutrients_with_units

    def get_nutrients_per_serving(self, obj):
        return obj.nutrients_per_serving_with_units


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Used for POST (create) and PUT/PATCH (update).

    Payload example:
    {
        "name": "Grilled Chicken Salad",
        "instructions": "...",
        "servings": 2,
        "cooking_duration": "30m",
        "category_name": "salads",
        "ingredients": [
            {"ingredient_name": "chicken breast", "quantity": 200, "unit_code": "g"},
            {"ingredient_name": "lettuce", "quantity": 100, "unit_code": "g"}
        ]
    }
    """
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True, required=False)
    category_name = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'instructions', 'servings',
            'category_name', 'ingredients',
        )
        extra_kwargs = {
            'name': {'validators': []},  # disable unique validator, get_or_create handles it
        }

    def _resolve_category(self, name):
        if not name:
            return None
        obj, _ = RecipeCategory.objects.get_or_create(name=name.strip().lower())
        return obj

    def _sync_ingredients(self, recipe, ingredients_data):
        """
        get_or_create each RecipeIngredient, update quantity/unit if it already exists.
        Does NOT delete ingredients that aren't in the payload (non-destructive).
        """
        for entry in ingredients_data:
            ri, created = RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                ingredient=entry['ingredient'],
                defaults={
                    'quantity': entry['quantity'],
                    'unit': entry['imu'],
                }
            )
            if not created:
                ri.quantity = entry['quantity']
                ri.unit = entry['imu']
                ri.save()

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        category_name = validated_data.pop('category_name', None)

        validated_data['category'] = self._resolve_category(category_name)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user

        recipe, _ = Recipe.objects.get_or_create(
            name=validated_data.pop('name').strip().lower(),
            defaults=validated_data,
        )

        self._sync_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        category_name = validated_data.pop('category_name', None)

        if category_name is not None:
            instance.category = self._resolve_category(category_name)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            instance.updated_by = request.user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if ingredients_data is not None:
            self._sync_ingredients(instance, ingredients_data)

        return instance


# ---------------------------------------------------------------------------
# INGREDIENT MEASUREMENT UNIT SERIALIZER
# ---------------------------------------------------------------------------

class IngredientMeasurementUnitSerializer(serializers.Serializer):
    """
    Used for POST /api/ingredients/<id>/units/
    Adds a measurement unit to an existing ingredient (get_or_create).

    Payload example:
    {
        "unit_code": "cup",
        "unit_name_singular": "cup",
        "unit_name_plural": "cups",
        "conversion_to_base": 240
    }

    If unit_code already exists as a MeasurementUnit, it is reused.
    If the unit is already linked to this ingredient, the conversion is updated.
    """
    unit_code = serializers.CharField(max_length=10)
    unit_name_singular = serializers.CharField(max_length=40, required=False)
    unit_name_plural = serializers.CharField(max_length=40, required=False)
    conversion_to_base = serializers.FloatField(min_value=0.01, max_value=100_000)

    def validate_unit_code(self, value):
        return value.strip().lower()

    def save(self, ingredient):
        unit_code = self.validated_data['unit_code']
        conversion = self.validated_data['conversion_to_base']
        name_singular = self.validated_data.get('unit_name_singular', unit_code)
        name_plural = self.validated_data.get('unit_name_plural', unit_code)

        # get_or_create the MeasurementUnit by code
        unit, _ = MeasurementUnit.objects.get_or_create(
            code=unit_code,
            defaults={
                'name_singular': name_singular,
                'name_plural': name_plural,
            }
        )

        # get_or_create the link between ingredient and unit
        imu, created = IngredientMeasurementUnit.objects.get_or_create(
            ingredient=ingredient,
            unit=unit,
            defaults={'conversion_to_base': conversion}
        )

        # if already linked, update the conversion
        if not created:
            imu.conversion_to_base = conversion
            imu.save()

        return imu