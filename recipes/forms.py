from datetime import time

from django import forms
from django.forms import inlineformset_factory

from .models import Recipe, RecipeIngredient, RecipeCategory
from ingredients.models import Ingredient, IngredientMeasurementUnit


class RecipeFormAdmin(forms.ModelForm):
    """
    Changes the input/edit option for the cooking time — default was time not duration.
    """
    class Meta:
        model = Recipe
        fields = '__all__'
        widgets = {
            'cooking_time': forms.TimeInput(format='%H:%M'),
        }


class RecipeForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=RecipeCategory.objects.all().order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'styled-input'})
    )

    created_by = forms.CharField(
        required=False, disabled=True, label='Created by',
        widget=forms.TextInput(attrs={'class': 'styled-input'})
    )
    updated_by = forms.CharField(
        required=False, disabled=True, label='Last updated by',
        widget=forms.TextInput(attrs={'class': 'styled-input'})
    )
    hours = forms.IntegerField(
        min_value=0, max_value=23, required=True, label="Hours", initial=0,
        widget=forms.NumberInput(attrs={'class': 'small-width styled-input', 'min': 0}),
        error_messages={
            'required': 'Please enter the cooking hours.',
            'min_value': 'Hours cannot be negative.',
            'max_value': 'Hours cannot exceed 23.',
            'invalid': 'Enter a whole number for hours.',
        }
    )
    minutes = forms.IntegerField(
        min_value=0, max_value=59, required=True, label="Minutes", initial=0,
        widget=forms.NumberInput(attrs={'class': 'small-width styled-input', 'min': 0}),
        error_messages={
            'required': 'Please enter the cooking minutes.',
            'max_value': 'Minutes cannot exceed 59.',
            'invalid': 'Enter a whole number for minutes.',
        }
    )
    servings = forms.IntegerField(
        min_value=1, initial=1,
        widget=forms.NumberInput(attrs={'class': 'small-width styled-input', 'min': 1, 'step': 1}),
        error_messages={
            'required': 'Please enter the number of servings.',
            'min_value': 'Servings must be at least 1.',
            'invalid': 'Enter a whole number for servings.',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['created_by'].initial = self.instance.created_by or '-'
            self.fields['updated_by'].initial = self.instance.updated_by or '-'
            self.fields['created_by'].widget.attrs['class'] = 'styled-input'
            self.fields['updated_by'].widget.attrs['class'] = 'styled-input'

        if self.instance and self.instance.cooking_time:
            self.fields['hours'].initial = self.instance.cooking_time.hour
            self.fields['minutes'].initial = self.instance.cooking_time.minute

    def clean_name(self):
        name = self.cleaned_data['name'].strip().lower()
        qs = Recipe.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'"{name}" already exists.')
        return name

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        h = self.cleaned_data.get('hours', 0)
        m = self.cleaned_data.get('minutes', 0)
        instance.cooking_time = time(hour=h, minute=m)
        instance.category = self.cleaned_data.get('category')
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Recipe
        exclude = ['cooking_time', 'ingredients', 'favourited_by', 'created_by', 'updated_by']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'styled-input'}),
            'instructions': forms.Textarea(attrs={'class': 'styled-input', 'style': "height: 35rem;"}),
        }


class RecipeIngredientForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        exclude = ['ingredientRecipe']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].queryset = IngredientMeasurementUnit.objects.none()

        if self.is_bound:
            ingredient_id = self.data.get(self.add_prefix('ingredient'))
            if ingredient_id:
                try:
                    self.fields['unit'].queryset = IngredientMeasurementUnit.objects.filter(
                        ingredient_id=int(ingredient_id)
                    )
                except (ValueError, TypeError):
                    pass

        elif self.instance.pk and self.instance.ingredient:
            self.fields['unit'].queryset = IngredientMeasurementUnit.objects.filter(
                ingredient=self.instance.ingredient
            )

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return quantity



RecipeIngredientFormSet = inlineformset_factory(
    Recipe, RecipeIngredient,
    form=RecipeIngredientForm,
    extra=0,
    can_delete=True
)