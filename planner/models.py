from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from ingredients.models import Ingredient, MeasurementUnit
from recipes.models import Recipe
from core.constants import UNIT_SYSTEM_CHOICES, DEFICIT_CHOICES, DEFICIT_VALUES, GENDER_CHOICES, ACTIVITY_CHOICES, ACTIVITY_MULTIPLIERS


# Create your models here.



class UserFridge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(default=0, validators=[MinValueValidator(0.01), MaxValueValidator(100_000)])
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('user', 'ingredient', 'unit')

    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name}"


class UserGroceryList(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(validators=[MinValueValidator(0.01), MaxValueValidator(100_000)])
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('user', 'ingredient', 'unit')

    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name}"


class GroceryListGeneration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grocery_generations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']


class GroceryListGenerationItem(models.Model):
    generation = models.ForeignKey(GroceryListGeneration, on_delete=models.CASCADE, related_name='items')
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True)
    quantity = models.FloatField(validators=[MinValueValidator(0.01), MaxValueValidator(100_000)])
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.ingredient} x{self.quantity} {self.unit}"


class UserMealList(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_list')
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True)
    made_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-made_at']

    def __str__(self):
        return f"{self.user.username} — {self.recipe.name if self.recipe else 'Deleted Recipe'} — {self.made_at.strftime('%Y-%m-%d %H:%M')}"


class UserBiometrics(models.Model):
    UNIT_SYSTEM_CHOICES = UNIT_SYSTEM_CHOICES
    DEFICIT_CHOICES = DEFICIT_CHOICES
    DEFICIT_VALUES = DEFICIT_VALUES
    GENDER_CHOICES = GENDER_CHOICES
    ACTIVITY_CHOICES =  ACTIVITY_CHOICES
    ACTIVITY_MULTIPLIERS = ACTIVITY_MULTIPLIERS

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='biometrics')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField(validators=[MinValueValidator(10), MaxValueValidator(120)])
    weight_kg = models.FloatField(validators=[MinValueValidator(20), MaxValueValidator(300)])
    height_cm = models.FloatField(validators=[MinValueValidator(50), MaxValueValidator(300)])
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='sedentary')
    unit_system = models.CharField(max_length=10, choices=UNIT_SYSTEM_CHOICES, default='metric')
    deficit_target = models.CharField(max_length=20, choices=DEFICIT_CHOICES, default='maintain')
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def target_calories(self):
        """TDEE adjusted for deficit target"""
        return round(self.tdee + self.DEFICIT_VALUES.get(self.deficit_target, 0), 2)

    @property
    def bmr(self) -> float:
        """
        Mifflin-St Jeor BMR — calories burned at complete rest (bed all day).
        Male:   10 * weight + 6.25 * height - 5 * age + 5
        Female: 10 * weight + 6.25 * height - 5 * age - 161
        """
        base = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age
        if self.gender == 'M':
            return round(base + 5, 2)
        return round(base - 161, 2)

    @property
    def tdee(self) -> float:
        """
        Total Daily Energy Expenditure — BMR adjusted for activity level.
        """
        multiplier = self.ACTIVITY_MULTIPLIERS.get(self.activity_level, 1.2)
        return round(self.bmr * multiplier, 2)

    def __str__(self):
        return f"{self.user.username} - BMR: {self.bmr} kcal | TDEE: {self.tdee} kcal"

    class Meta:
        verbose_name = "User Biometrics"
        verbose_name_plural = "User Biometrics"


class CalendarEntry(models.Model):
    SOURCE_CHOICES = [
        ('manual_recipe', 'Manual Recipe'),
        ('manual_ingredient', 'Manual Ingredient'),
        ('meal_suggestion', 'Meal Suggestion'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calendar_entries')
    date = models.DateField()
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.SET_NULL, null=True, blank=True)
    ingredient = models.ForeignKey('ingredients.Ingredient', on_delete=models.SET_NULL, null=True, blank=True)
    ingredient_unit = models.ForeignKey('ingredients.MeasurementUnit', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.01)])
    servings = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.01)])
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual_recipe')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        if self.recipe:
            return f"{self.user.username} — {self.recipe.name} on {self.date}"
        if self.ingredient:
            return f"{self.user.username} — {self.ingredient.name} on {self.date}"
        return f"{self.user.username} on {self.date}"

    @property
    def kcal(self):
        if self.recipe and self.servings:
            return round(self.recipe.kcal_per_serving * self.servings, 2)
        if self.ingredient and self.quantity and self.ingredient_unit:
            from ingredients.models import IngredientMeasurementUnit
            try:
                imu = IngredientMeasurementUnit.objects.get(ingredient=self.ingredient, unit=self.ingredient_unit)
                nutrients = self.ingredient.get_nutrients_dict(imu, self.quantity)
                return round(nutrients.get('kcal', 0), 2)
            except Exception:
                return 0
        return 0