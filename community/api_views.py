from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.utils import timezone
from django.db.models import Avg
from datetime import timedelta
from .models import (
    Review, ReviewHelpful, WeeklyRanking, TrendingDish,
    CommunityChallenge, ChallengeParticipation, UserBadge
)
from .serializers import (
    ReviewSerializer, WeeklyRankingSerializer, TrendingDishSerializer,
    CommunityChallengeSerializer, ChallengeParticipationSerializer,
    UserBadgeSerializer
)


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Review"""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.select_related('user', 'dish', 'dish__cuisine')

        # Filter by dish
        dish_id = self.request.query_params.get('dish')
        if dish_id:
            queryset = queryset.filter(dish_id=dish_id)

        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        # Check if user already reviewed this dish
        dish_id = request.data.get('dish_id')
        if Review.objects.filter(user=request.user, dish_id=dish_id).exists():
            return Response(
                {"error": "You've already reviewed this dish"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(user=request.user)

        # Update dish rating
        dish = review.dish
        avg_rating = Review.objects.filter(dish=dish).aggregate(Avg('rating'))['rating__avg']
        dish.average_rating = round(avg_rating, 2)
        dish.total_ratings += 1
        dish.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_helpful(self, request, pk=None):
        """Mark a review as helpful"""
        review = self.get_object()

        # Check if already marked helpful
        helpful, created = ReviewHelpful.objects.get_or_create(
            user=request.user,
            review=review
        )

        if not created:
            helpful.delete()
            review.helpful_count = max(0, review.helpful_count - 1)
            review.save()
            return Response({"status": "unmarked"}, status=status.HTTP_200_OK)
        else:
            review.helpful_count += 1
            review.save()
            return Response({"status": "marked"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_reviews(self, request):
        """Get current user's reviews"""
        reviews = Review.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)


class WeeklyRankingView(APIView):
    """Get weekly dish rankings"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        # Get current week or specific week
        week_offset = int(request.query_params.get('week_offset', 0))

        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday() + (7 * week_offset))
        week_end = week_start + timedelta(days=6)

        rankings = WeeklyRanking.objects.filter(
            week_start=week_start
        ).select_related('dish', 'dish__cuisine').order_by('rank')[:10]

        if not rankings.exists():
            return Response({
                'week_start': week_start,
                'week_end': week_end,
                'rankings': [],
                'message': 'No rankings available for this week'
            })

        serializer = WeeklyRankingSerializer(rankings, many=True)
        return Response({
            'week_start': week_start,
            'week_end': week_end,
            'rankings': serializer.data
        })


class TrendingDishView(APIView):
    """Get trending dishes"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))

        trending = TrendingDish.objects.select_related(
            'dish', 'dish__cuisine'
        ).order_by('-trending_score')[:limit]

        serializer = TrendingDishSerializer(trending, many=True)
        return Response(serializer.data)


class CommunityChallengeViewSet(viewsets.ModelViewSet):
    """ViewSet for CommunityChallenge"""
    serializer_class = CommunityChallengeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = CommunityChallenge.objects.select_related('target_dish')

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            # Default to active and upcoming
            queryset = queryset.filter(status__in=['active', 'upcoming'])

        return queryset.order_by('-start_date')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """Join a challenge"""
        challenge = self.get_object()

        if challenge.status != 'active':
            return Response(
                {"error": "Challenge is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )

        participation, created = ChallengeParticipation.objects.get_or_create(
            user=request.user,
            challenge=challenge
        )

        if not created:
            return Response(
                {"error": "Already participating in this challenge"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            ChallengeParticipationSerializer(participation).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def leave(self, request, pk=None):
        """Leave a challenge"""
        challenge = self.get_object()

        participation = ChallengeParticipation.objects.filter(
            user=request.user,
            challenge=challenge
        ).first()

        if not participation:
            return Response(
                {"error": "Not participating in this challenge"},
                status=status.HTTP_404_NOT_FOUND
            )

        participation.delete()
        return Response({"status": "left"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_challenges(self, request):
        """Get user's challenges"""
        participations = ChallengeParticipation.objects.filter(
            user=request.user
        ).select_related('challenge', 'challenge__target_dish')

        serializer = ChallengeParticipationSerializer(participations, many=True)
        return Response(serializer.data)


class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for UserBadge (read-only)"""
    serializer_class = UserBadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).order_by('-earned_at')

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available badges to earn"""
        # This would contain logic for available badges
        # For now, returning empty list
        return Response([])
