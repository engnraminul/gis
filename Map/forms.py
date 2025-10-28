from django import forms
from .models import Map
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _



class MapForm(forms.ModelForm):
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'multiple': True,
            'class': 'form-control',
            'accept': '.shp,.csv,.geojson,.kmz,.kml,.zip',
        }),
        required=False,
        label="Upload Map Files",
        help_text="Supported formats: .shp, .csv, .geojson, .kmz, .kml, .zip"
    )
    title = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter map title',
            'maxlength': 100
        }),
        label="Map Title"
    )
    thumbnail = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
        }),
        required=False,
        label="Thumbnail Image"
    )
    # Removed status field from form

    class Meta:
        model = Map
        exclude = ['user', 'publishing_date', 'status', 'views_count']

    

    def clean_title(self):
        title = self.cleaned_data.get('title')
        
        # Check if title is empty
        if not title:
            raise forms.ValidationError("Title is required.")  # Custom validation message

        # Optionally, check if title already exists in the database
        if Map.objects.filter(title__iexact=title).exists():
            raise forms.ValidationError("A map with this title already exists.")  # Custom validation message
        
        # You can also validate the length of the title, for example:
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")

        return title

    def clean_files(self):
        files = self.files.getlist('files') if hasattr(self.files, 'getlist') else [self.cleaned_data.get('files')]
        allowed_extensions = ['.shp', '.csv', '.geojson', '.kmz', '.kml', '.zip']
        for f in files:
            if f:
                if not any(f.name.lower().endswith(e) for e in allowed_extensions):
                    raise forms.ValidationError(
                        "Only shapefile (.shp, .zip), csv, geojson, kmz, and kml files are allowed."
                    )
        return files
