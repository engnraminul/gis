from django.forms.widgets import ClearableFileInput

class CustomClearableFileInput(ClearableFileInput):
    allow_multiple_selected = True

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs['multiple'] = 'multiple'
        return super().render(name, value, attrs, renderer)
