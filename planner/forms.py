from django import forms
from .models import UserFridge, UserBiometrics
from core.mixins import ErrorMessagesMixin

class UserFridgeForm(ErrorMessagesMixin, forms.ModelForm):
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


class BiometricsForm(forms.ModelForm):
    class Meta:
        model = UserBiometrics
        fields = ['gender', 'age', 'weight_kg', 'height_cm', 'activity_level']
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'age': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Age'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Weight (kg)'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Height (cm)'}),
            'activity_level': forms.Select(attrs={'class': 'form-input'}),
        }