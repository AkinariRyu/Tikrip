from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email адреса")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')