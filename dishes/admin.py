from django.contrib import admin
from .models import Cuisine, Dish, Restaurant, RestaurantDish, DishIngredient


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ['emoji', 'name', 'description']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['name', 'cuisine', 'meal_type', 'calories', 'average_rating', 'total_swipes', 'match_rate',
                    'is_active']
    list_filter = ['cuisine', 'meal_type', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['average_rating', 'total_ratings', 'total_swipes', 'total_right_swipes', 'created_at',
                       'updated_at']
    list_editable = ['is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'cuisine', 'meal_type')
        }),
        ('Nutrition', {
            'fields': ('calories', 'protein', 'carbs', 'fat')
        }),
        ('Dietary & Preferences', {
            'fields': ('is_vegetarian', 'is_vegan', 'is_gluten_free', 'spice_level')
        }),
        ('Media', {
            'fields': ('image', 'image_url')
        }),
        ('Stats', {
            'fields': ('average_rating', 'total_ratings', 'total_swipes', 'total_right_swipes'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'price_range', 'rating', 'cuisine_type', 'is_active']
    list_filter = ['city', 'price_range', 'cuisine_type', 'is_active', 'has_uber_eats', 'has_doordash', 'has_grubhub']
    search_fields = ['name', 'address', 'city']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'cuisine_type', 'price_range')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code', 'latitude', 'longitude')
        }),
        ('Contact', {
            'fields': ('phone', 'website')
        }),
        ('Ratings', {
            'fields': ('rating', 'total_reviews')
        }),
        ('Delivery Options', {
            'fields': ('has_uber_eats', 'uber_eats_url', 'has_doordash', 'doordash_url', 'has_grubhub', 'grubhub_url')
        }),
        ('External IDs', {
            'fields': ('google_place_id', 'yelp_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )


@admin.register(RestaurantDish)
class RestaurantDishAdmin(admin.ModelAdmin):
    list_display = ['dish', 'restaurant', 'price', 'is_available']
    list_filter = ['is_available', 'restaurant']
    search_fields = ['dish__name', 'restaurant__name']
    list_editable = ['price', 'is_available']


@admin.register(DishIngredient)
class DishIngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'dish', 'is_allergen']
    list_filter = ['is_allergen', 'dish']
    search_fields = ['name', 'dish__name']