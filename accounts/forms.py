from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationForm(UserCreationForm):
    """Extended user registration form"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""

    class Meta:
        model = UserProfile
        fields = [
            'city',
            'bio',
            'profile_picture',
            'diet_type',
            'allergies',
            'favorite_cuisines',
            'daily_calorie_goal',
            'protein_goal',
            'carbs_goal',
            'fat_goal',
            'preferred_delivery_app',
            'max_distance_miles',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about your food journey...'}),
            'allergies': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g., peanuts, shellfish, dairy'
            }),
            'favorite_cuisines': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g., Italian, Mexican, Chinese, Indian'
            }),
            'city': forms.TextInput(attrs={'placeholder': 'Your city'}),
            'max_distance_miles': forms.NumberInput(attrs={'step': '0.5', 'min': '1', 'max': '50'}),
        }
        help_texts = {
            'daily_calorie_goal': 'Target daily calories (optional)',
            'protein_goal': 'Target protein in grams (optional)',
            'carbs_goal': 'Target carbs in grams (optional)',
            'fat_goal': 'Target fat in grams (optional)',
        }


class UserUpdateForm(forms.ModelForm):
    """Form for updating basic user info"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("This email is already in use.")
        return email