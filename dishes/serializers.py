from rest_framework import serializers
from .models import Cuisine, Dish, Restaurant, RestaurantDish, DishIngredient


class CuisineSerializer(serializers.ModelSerializer):
    """Serializer for Cuisine"""

    class Meta:
        model = Cuisine
        fields = ['id', 'name', 'description', 'emoji']


class DishIngredientSerializer(serializers.ModelSerializer):
    """Serializer for DishIngredient"""

    class Meta:
        model = DishIngredient
        fields = ['id', 'name', 'is_allergen']


class DishSerializer(serializers.ModelSerializer):
    """Serializer for Dish"""

    cuisine = CuisineSerializer(read_only=True)
    cuisine_id = serializers.PrimaryKeyRelatedField(
        queryset=Cuisine.objects.all(), source='cuisine', write_only=True, required=False
    )
    ingredients = DishIngredientSerializer(many=True, read_only=True)
    display_image = serializers.ReadOnlyField()
    match_rate = serializers.ReadOnlyField()

    class Meta:
        model = Dish
        fields = [
            'id', 'name', 'description', 'cuisine', 'cuisine_id',
            'calories', 'protein', 'carbs', 'fat', 'meal_type',
            'is_vegetarian', 'is_vegan', 'is_gluten_free', 'spice_level',
            'image', 'image_url', 'display_image', 'average_rating',
            'total_ratings', 'total_swipes', 'total_right_swipes', 'match_rate',
            'created_at', 'updated_at', 'is_active', 'ingredients'
        ]
        read_only_fields = [
            'average_rating', 'total_ratings', 'total_swipes',
            'total_right_swipes', 'created_at', 'updated_at'
        ]


class DishCardSerializer(serializers.ModelSerializer):
    """Lightweight serializer for swipe cards"""

    cuisine = CuisineSerializer(read_only=True)
    display_image = serializers.ReadOnlyField()
    match_rate = serializers.ReadOnlyField()

    class Meta:
        model = Dish
        fields = [
            'id', 'name', 'description', 'cuisine', 'calories',
            'meal_type', 'is_vegetarian', 'is_vegan', 'is_gluten_free',
            'spice_level', 'display_image', 'average_rating', 'match_rate'
        ]


class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer for Restaurant"""

    cuisine_type = CuisineSerializer(read_only=True)
    cuisine_type_id = serializers.PrimaryKeyRelatedField(
        queryset=Cuisine.objects.all(), source='cuisine_type', write_only=True, required=False
    )
    full_address = serializers.ReadOnlyField()
    delivery_options = serializers.ReadOnlyField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'city', 'state', 'zip_code',
            'full_address', 'latitude', 'longitude', 'phone', 'website',
            'price_range', 'cuisine_type', 'cuisine_type_id', 'rating', 'total_reviews',
            'has_uber_eats', 'has_doordash', 'has_grubhub',
            'uber_eats_url', 'doordash_url', 'grubhub_url',
            'delivery_options', 'google_place_id', 'yelp_id',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at']


class RestaurantDishSerializer(serializers.ModelSerializer):
    """Serializer for RestaurantDish junction"""

    restaurant = RestaurantSerializer(read_only=True)
    dish = DishSerializer(read_only=True)

    class Meta:
        model = RestaurantDish
        fields = ['id', 'restaurant', 'dish', 'price', 'is_available', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class RestaurantWithDistanceSerializer(RestaurantSerializer):
    """Restaurant serializer with distance field"""

    distance = serializers.FloatField(read_only=True)
    estimated_delivery_time = serializers.IntegerField(read_only=True)
    dish_price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta(RestaurantSerializer.Meta):
        fields = RestaurantSerializer.Meta.fields + ['distance', 'estimated_delivery_time', 'dish_price']
