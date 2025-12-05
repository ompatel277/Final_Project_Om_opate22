from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'diet_type', 'preferred_delivery_app', 'created_at']
    list_filter = ['diet_type', 'preferred_delivery_app', 'created_at']
    search_fields = ['user__username', 'user__email', 'city']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'city', 'bio', 'profile_picture')
        }),
        ('Dietary Preferences', {
            'fields': ('diet_type', 'allergies', 'favorite_cuisines')
        }),
        ('Nutrition Goals', {
            'fields': ('daily_calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal')
        }),
        ('App Settings', {
            'fields': ('preferred_delivery_app', 'max_distance_miles')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )