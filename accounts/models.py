from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile with food preferences and settings"""

    DIET_CHOICES = [
        ('none', 'No Restriction'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('pescatarian', 'Pescatarian'),
        ('keto', 'Keto'),
        ('paleo', 'Paleo'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
    ]

    DELIVERY_CHOICES = [
        ('ubereats', 'Uber Eats'),
        ('doordash', 'DoorDash'),
        ('grubhub', 'Grubhub'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Personal Information
    city = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Dietary Preferences
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES, default='none')
    allergies = models.TextField(
        blank=True,
        help_text="Comma-separated list of allergies (e.g., peanuts, shellfish, dairy)"
    )
    favorite_cuisines = models.TextField(
        blank=True,
        help_text="Comma-separated list of favorite cuisines (e.g., Italian, Mexican, Chinese)"
    )

    # Nutrition Goals
    daily_calorie_goal = models.IntegerField(null=True, blank=True)
    protein_goal = models.IntegerField(null=True, blank=True, help_text="grams")
    carbs_goal = models.IntegerField(null=True, blank=True, help_text="grams")
    fat_goal = models.IntegerField(null=True, blank=True, help_text="grams")

    # App Settings
    preferred_delivery_app = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='ubereats'
    )
    max_distance_miles = models.FloatField(default=5.0, help_text="Maximum distance for restaurants")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_allergies_list(self):
        """Return list of allergies"""
        if self.allergies:
            return [a.strip() for a in self.allergies.split(',')]
        return []

    def get_favorite_cuisines_list(self):
        """Return list of favorite cuisines"""
        if self.favorite_cuisines:
            return [c.strip() for c in self.favorite_cuisines.split(',')]
        return []

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# Signal to auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()