from django import forms
from .models import Profile  # Import your Profile model

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'phone', 'email', 'address', 'profile_picture']