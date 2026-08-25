from django import forms
from django.core.validators import MinValueValidator

from core.constants import NUTRIENTS, NUTRIENT_UNITS
from .models import Ingredient, IngredientMeasurementUnit
from core.mixins import ErrorMessagesMixin, StyledFormMixin


class IngredientFormBase(StyledFormMixin, ErrorMessagesMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.apply_error_messages(['name', 'base_quantity', 'default_unit'])
        self.fields['dietary_tag'].required = False
        self.fields['base_quantity'].validators.append(MinValueValidator(0.01))
        self.fields['base_quantity'].error_messages['min_value'] = 'Base quantity must be greater than 0.'

        for nutrient in NUTRIENTS:
            field = f'base_quantity_{nutrient}'
            unit = NUTRIENT_UNITS.get(nutrient, '')
            self.fields[field].label = f"{nutrient.replace('_', ' ').title()} ({unit})"
            self.fields[field].required = False
            self.fields[field].initial = 0
            self.fields[field].widget = forms.NumberInput(
                attrs={'class': ' nutrient-input styled-input', 'step': 'any', 'min': 0}
            )

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Ingredient.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(f'"{name}" already exists.')
        return name


    def save(self, commit=True):
        """
        ensures default unit selected upon ingredient creation exist in IngredientMeasurementUnit table
        else it creates it
        """
        ingredient = super().save(commit=commit)
        if commit:
            IngredientMeasurementUnit.objects.get_or_create(
                ingredient=ingredient,
                unit=ingredient.default_unit,
                conversion_to_base=ingredient.base_quantity
            )
        return ingredient


    class Meta:
        model = Ingredient
        fields = (
            ['name', 'category', 'dietary_tag', 'base_quantity', 'default_unit'] +
            [f'base_quantity_{n}' for n in NUTRIENTS]
        )

        widgets = {
            'name': forms.TextInput(attrs={'class': ''}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'dietary_tag': forms.CheckboxSelectMultiple(),
            'default_unit': forms.Select(attrs={'class': 'form-select'}),
            'base_quantity': forms.NumberInput(attrs={'min': 0.01}),
        }


class IngredientAddForm(IngredientFormBase):
    ...


class IngredientEditForm(IngredientFormBase):
    created_by = forms.CharField(required=False, disabled=True)
    updated_by = forms.CharField(required=False, disabled=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['created_by'].initial = self.instance.created_by or '-'
            self.fields['updated_by'].initial = self.instance.updated_by or '-'
            self.fields['created_by'].widget.attrs['class'] = ' styled-input'
            self.fields['updated_by'].widget.attrs['class'] = ' styled-input'


    def clean_name(self):
        """
        IngredientFormBase will wrongly flag the ingredient's OWN current name as a duplicate, hence rewriting
        """
        name = self.cleaned_data['name'].strip()
        qs = Ingredient.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'"{name}" already exists.')
        return name


class IngredientDetailForm(StyledFormMixin, forms.Form):
    def __init__(self, ingredient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ingredient = ingredient
        self.default_imu = IngredientMeasurementUnit.objects.filter(
            ingredient=ingredient,
            unit=ingredient.default_unit
        ).first()  # returns None instead of raising DoesNotExist

        self.fields['unit'].queryset = IngredientMeasurementUnit.objects.filter(
            ingredient=ingredient
        )

    quantity = forms.FloatField(
        min_value=0.01,
        error_messages={
            'required': 'Please enter a quantity.',
            'invalid': 'Please enter a valid quantity.',
            'min_value': 'Quantity must be greater than 0.',
        },
        widget=forms.NumberInput(attrs={'class': '', 'step': 'any', 'min': 0.01})
    )
    unit = forms.ModelChoiceField(
        queryset=IngredientMeasurementUnit.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def get_unit(self):
        if self.is_valid():
            return self.cleaned_data['unit'] or self.default_imu
        return self.default_imu

    def get_quantity(self):
        if self.is_valid():
            return self.cleaned_data['quantity']
        return self.ingredient.base_quantity

    def get_nutrients(self):
        ingredient = self.ingredient
        unit = self.get_unit()
        quantity = self.get_quantity()

        nutrients_dict = ingredient.get_nutrients_dict(ingredient_unit=unit, quantity=quantity)
        return {
            n: f"{round(v, 2)} {ingredient.NUTRIENT_UNITS.get(n, '')}"
            for n, v in nutrients_dict.items()
        }