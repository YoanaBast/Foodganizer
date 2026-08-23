from django import forms
from .models import UserFridge, UserBiometrics
from core.mixins import ErrorMessagesMixin
from core.mixins import StyledFormMixin

class UserFridgeForm(StyledFormMixin, ErrorMessagesMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_error_messages(['quantity', 'unit'])

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None or quantity < 0.01:
            raise forms.ValidationError('Quantity must be at least 0.01.')
        return quantity

    class Meta:
        model = UserFridge
        exclude = ['user', 'ingredient']


class BiometricsForm(StyledFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' styled-input').strip()

    # display-only fields for imperial input
    weight_lbs = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Weight (lbs)'})
    )
    height_ft = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Feet'})
    )
    height_in = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Inches'})
    )

    class Meta:
        model = UserBiometrics
        fields = ['gender', 'age', 'weight_kg', 'height_cm', 'activity_level', 'unit_system', 'deficit_target']
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'age': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Age'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Weight (kg)'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Height (cm)'}),
            'activity_level': forms.Select(attrs={'class': 'form-input'}),
            'unit_system': forms.Select(attrs={'class': 'form-input', 'id': 'id_unit_system'}),
            'deficit_target': forms.RadioSelect(),
        }

    def clean(self):
        cleaned_data = super().clean()
        unit_system = cleaned_data.get('unit_system')

        if unit_system == 'imperial':
            weight_lbs = cleaned_data.get('weight_lbs')
            height_ft = cleaned_data.get('height_ft')
            height_in = cleaned_data.get('height_in', 0) or 0

            if weight_lbs:
                cleaned_data['weight_kg'] = round(weight_lbs * 0.453592, 2)
            if height_ft:
                total_inches = (height_ft * 12) + height_in
                cleaned_data['height_cm'] = round(total_inches * 2.54, 2)

        return cleaned_data