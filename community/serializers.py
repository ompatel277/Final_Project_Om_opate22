from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Review, ReviewHelpful, WeeklyRanking, TrendingDish,
    CommunityChallenge, ChallengeParticipation, UserBadge
)
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


class WeeklyRankingSerializer(serializers.ModelSerializer):
    """Serializer for WeeklyRanking"""

    dish = DishCardSerializer(read_only=True)
    match_rate = serializers.ReadOnlyField()

    class Meta:
        model = WeeklyRanking
        fields = [
            'id', 'dish', 'week_start', 'week_end', 'rank',
            'total_swipes', 'right_swipes', 'reviews_count',
            'average_rating', 'match_rate', 'created_at'
        ]
        read_only_fields = ['created_at']


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


class CommunityChallengeSerializer(serializers.ModelSerializer):
    """Serializer for CommunityChallenge"""

    target_dish = DishCardSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_participating = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = CommunityChallenge
        fields = [
            'id', 'title', 'description', 'challenge_type',
            'start_date', 'end_date', 'status', 'target_dish',
            'target_cuisine', 'reward_description', 'image',
            'participants_count', 'is_participating', 'user_progress',
            'created_at'
        ]
        read_only_fields = ['created_at']

    def get_participants_count(self, obj):
        return obj.participants.count()

    def get_is_participating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(id=request.user.id).exists()
        return False

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participation = ChallengeParticipation.objects.filter(
                user=request.user, challenge=obj
            ).first()
            if participation:
                return {
                    'progress_count': participation.progress_count,
                    'completed': participation.completed,
                    'joined_at': participation.joined_at
                }
        return None


class ChallengeParticipationSerializer(serializers.ModelSerializer):
    """Serializer for ChallengeParticipation"""

    challenge = CommunityChallengeSerializer(read_only=True)

    class Meta:
        model = ChallengeParticipation
        fields = [
            'id', 'challenge', 'completed', 'progress_count',
            'joined_at', 'completed_at'
        ]
        read_only_fields = ['joined_at']


class UserBadgeSerializer(serializers.ModelSerializer):
    """Serializer for UserBadge"""

    class Meta:
        model = UserBadge
        fields = ['id', 'badge_type', 'name', 'description', 'icon', 'earned_at']
        read_only_fields = ['earned_at']
