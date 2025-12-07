from rest_framework import serializers
from django.contrib.auth.models import User
from .models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist, SwipeSession
from dishes.models import Dish, Restaurant
from dishes.serializers import DishCardSerializer, DishSerializer, RestaurantSerializer


class SwipeActionSerializer(serializers.ModelSerializer):
    """Serializer for SwipeAction"""

    dish = DishCardSerializer(read_only=True)
    dish_id = serializers.PrimaryKeyRelatedField(
        queryset=Dish.objects.all(), source='dish', write_only=True
    )

    class Meta:
        model = SwipeAction
        fields = ['id', 'dish', 'dish_id', 'direction', 'created_at']
        read_only_fields = ['created_at']


class SwipeActionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating swipe actions"""

    class Meta:
        model = SwipeAction
        fields = ['dish', 'direction']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        swipe = SwipeAction.objects.create(**validated_data)

        # Update dish statistics
        dish = validated_data['dish']
        dish.total_swipes += 1
        if validated_data['direction'] == 'right':
            dish.total_right_swipes += 1
        dish.save()

        return swipe


class FavoriteSerializer(serializers.ModelSerializer):
    """Serializer for Favorite"""

    dish = DishSerializer(read_only=True)
    dish_id = serializers.PrimaryKeyRelatedField(
        queryset=Dish.objects.all(), source='dish', write_only=True
    )

    class Meta:
        model = Favorite
        fields = ['id', 'dish', 'dish_id', 'notes', 'created_at']
        read_only_fields = ['created_at']


class FavoriteRestaurantSerializer(serializers.ModelSerializer):
    """Serializer for FavoriteRestaurant"""

    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(), source='restaurant', write_only=True
    )

    class Meta:
        model = FavoriteRestaurant
        fields = ['id', 'restaurant', 'restaurant_id', 'notes', 'created_at']
        read_only_fields = ['created_at']


class BlacklistSerializer(serializers.ModelSerializer):
    """Serializer for Blacklist"""

    dish = DishCardSerializer(read_only=True, required=False)

    class Meta:
        model = Blacklist
        fields = ['id', 'blacklist_type', 'item_name', 'reason', 'dish', 'created_at']
        read_only_fields = ['created_at']


class SwipeSessionSerializer(serializers.ModelSerializer):
    """Serializer for SwipeSession"""

    match_rate = serializers.ReadOnlyField()

    class Meta:
        model = SwipeSession
        fields = [
            'id', 'total_swipes', 'right_swipes', 'left_swipes',
            'match_rate', 'started_at', 'ended_at',
            'cuisine_filter', 'meal_type_filter'
        ]
        read_only_fields = ['started_at']


class SwipeStatsSerializer(serializers.Serializer):
    """Serializer for user swipe statistics"""

    total_swipes = serializers.IntegerField()
    right_swipes = serializers.IntegerField()
    left_swipes = serializers.IntegerField()
    match_rate = serializers.FloatField()
    favorite_cuisines = serializers.ListField(child=serializers.DictField())
    most_swiped_meal_type = serializers.CharField()
    total_favorites = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
