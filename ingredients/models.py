from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.constants import NUTRIENTS, NUTRIENT_UNITS
from core.models import TrackingMixin


# Create your models here.


class IngredientDietaryTag(TrackingMixin, models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ingredient Dietary Tag"
        verbose_name_plural = "Ingredient Dietary Tags"


class IngredientCategory(TrackingMixin, models.Model):
    name = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ingredient Category"
        verbose_name_plural = "Ingredient Categories"


class MeasurementUnit(TrackingMixin, models.Model):
    code = models.CharField(max_length=10, unique=True)
    name_singular = models.CharField(max_length=40)
    name_plural = models.CharField(max_length=40)

    def __str__(self):
        return f"{self.name_singular} ({self.code})"


class IngredientMeasurementUnit(models.Model):
    """
    allows ingredients to have multiple measurement units - like grams and cups, conversion to base will be 1 for the main unit
    """
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE, related_name='measurement_units')
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE)

    conversion_to_base = models.FloatField(default=1, validators=[MinValueValidator(0.01), MaxValueValidator(100_000)], help_text="How much of this unit equals the base_quantity")
    # 1 cup of carrot ≈ 120 g → conversion_to_base = 120

    def name_for_quantity(self, quantity=1):
        return self.unit.name_singular if quantity == 1 else self.unit.name_plural

    @property
    def name_for_quantity_singular(self):
        return self.unit.name_singular

    @property
    def name_for_quantity_plural(self):
        return self.unit.name_plural

    def __str__(self):
        return f"{self.ingredient.name} - {self.unit}"


class Ingredient(TrackingMixin, models.Model):
    NUTRIENTS = NUTRIENTS
    NUTRIENT_UNITS = NUTRIENT_UNITS
    # init because will use in loop

    name = models.CharField(max_length=100, unique=True)

    default_unit = models.ForeignKey('MeasurementUnit', on_delete=models.SET_NULL, null=True, related_name='+') #no reverse
    #the unit that holds the nutrient data for conversions

    base_quantity = models.FloatField(default=100, validators=[MinValueValidator(0.01), MaxValueValidator(100_000)],
                                      help_text="The quantity the NUTRIENTS are based on in default_unit (100 g, 1 pc, etc.)")
    #base_quantity = 100 means nutrients are defined per 100g

    category = models.ForeignKey(IngredientCategory, null=True, on_delete=models.SET_NULL, related_name='ingredient')
    # discourage users from creating lazy ingredients, but if deleting a category, keep the ingredients

    dietary_tag = models.ManyToManyField(IngredientDietaryTag, blank=True,  related_name='ingredient')
    #ManyToManyField does not use null=True because the relation is stored in a separate join table

    for nutrient in NUTRIENTS:
        locals()[f'base_quantity_{nutrient}'] = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100_000)], )
    #dynamically creates a model field for each nutrient in the NUTRIENTS list

    @property
    def dietary_info(self):
        """Return dietary tags as a comma-separated string"""
        return ", ".join(tag.name for tag in self.dietary_tag.all()) or "-"

    def get_nutrients_dict(self, ingredient_unit: 'IngredientMeasurementUnit', quantity: float):
        """Return a dics of all nutrients per unit and quantity"""
        if ingredient_unit == self.default_unit:
            quantity_in_base_units = quantity
        else:
            quantity_in_base_units = quantity * ingredient_unit.conversion_to_base

        nutrients = {}
        for n in self.NUTRIENTS:
            nutrient_base_value = getattr(self, f'base_quantity_{n}', 0)
            # scale nutrient proportionally to quantity
            nutrients[n] = nutrient_base_value * (quantity_in_base_units / self.base_quantity)

        return nutrients

    @property
    def nutrients(self):
        """Return a dict of all nutrient fields with their base values -> for visualization"""
        return {n: getattr(self, f'base_quantity_{n}', 0) for n in self.NUTRIENTS}

    @property
    def nutrients_with_units(self):
        """Return nutrients with units, using NUTRIENT_UNITS dict"""
        return {n: f"{getattr(self, f'base_quantity_{n}', 0)} {self.NUTRIENT_UNITS.get(n, '')}"
                for n in self.NUTRIENTS}

    def nutrients_for_quantity(self, ingredient_unit, quantity):
        nutrients_dict = self.get_nutrients_dict(ingredient_unit, quantity)
        return {n: f"{round(v, 2)} {self.NUTRIENT_UNITS.get(n, '')}" for n, v in nutrients_dict.items()}

    def __str__(self):
        return self.name