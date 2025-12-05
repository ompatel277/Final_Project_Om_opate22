from django.contrib import admin
from .models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist, SwipeSession


@admin.register(SwipeAction)
class SwipeActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'dish', 'direction', 'created_at']
    list_filter = ['direction', 'created_at']
    search_fields = ['user__username', 'dish__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'dish', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'dish__name']
    readonly_fields = ['created_at']


@admin.register(FavoriteRestaurant)
class FavoriteRestaurantAdmin(admin.ModelAdmin):
    list_display = ['user', 'restaurant', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'restaurant__name']
    readonly_fields = ['created_at']


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_name', 'blacklist_type', 'created_at']
    list_filter = ['blacklist_type', 'created_at']
    search_fields = ['user__username', 'item_name']
    readonly_fields = ['created_at']


@admin.register(SwipeSession)
class SwipeSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_swipes', 'right_swipes', 'left_swipes', 'match_rate', 'started_at']
    list_filter = ['started_at']
    search_fields = ['user__username']
    readonly_fields = ['started_at', 'ended_at']

    def match_rate(self, obj):
        return f"{obj.match_rate}%"

    match_rate.short_description = "Match Rate"