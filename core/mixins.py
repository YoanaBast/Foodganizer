class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'profile_picture':
                continue  # leave the file input untouched — custom upload button handles its styling
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' styled-input').strip()



class ErrorMessagesMixin:
    default_error_messages = {
        'name': {
            'required': 'Please enter a name.',
            'unique': 'This name already exists.',
            'max_length': 'Name is too long — maximum 100 characters.',
        },
        'base_quantity': {
            'required': 'Please enter a base quantity.',
            'invalid': 'Enter a valid number.',
            'min_value': 'Base quantity must be greater than 0.',
        },
        'default_unit': {
            'required': 'Please select a measurement unit.',
        },
        'quantity': {
            'required': 'Please enter a quantity.',
            'invalid': 'Enter a valid number.',
            'min_value': 'Quantity must be greater than 0.',
        },
        'unit': {
            'required': 'Please select a unit.',
        },
    }

    def apply_error_messages(self, fields=None):
        fields = fields or list(self.default_error_messages.keys())
        for field_name in fields:
            if field_name in self.fields and field_name in self.default_error_messages:
                self.fields[field_name].error_messages.update(
                    self.default_error_messages[field_name]
                )


from django.core.exceptions import PermissionDenied

class OwnerOrModeratorMixin:
    owner_field = 'created_by'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user.groups.filter(name='Moderator').exists():
            return obj
        if getattr(obj, self.owner_field) != self.request.user:
            raise PermissionDenied
        return obj