from rest_framework import serializers
from .models import Review, ReviewHelpful, TrendingDish
from dishes.serializers import DishCardSerializer, DishSerializer


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review"""

    user = serializers.StringRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    dish = DishCardSerializer(read_only=True)
    dish_id = serializers.PrimaryKeyRelatedField(
        queryset=DishSerializer.Meta.model.objects.all(),
        source='dish',
        write_only=True
    )
    is_helpful = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'username', 'dish', 'dish_id', 'rating',
            'title', 'content', 'image', 'helpful_count',
            'is_helpful', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['helpful_count', 'is_verified', 'created_at', 'updated_at']

    def get_is_helpful(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ReviewHelpful.objects.filter(user=request.user, review=obj).exists()
        return False


class TrendingDishSerializer(serializers.ModelSerializer):
    """Serializer for TrendingDish"""

    dish = DishCardSerializer(read_only=True)

    class Meta:
        model = TrendingDish
        fields = [
            'id', 'dish', 'trending_score', 'recent_swipes_24h',
            'recent_swipes_7d', 'recent_reviews_7d', 'current_rank',
            'last_updated'
        ]
        read_only_fields = ['last_updated']
