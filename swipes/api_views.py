from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from .models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist, SwipeSession
from .serializers import (
    SwipeActionSerializer, SwipeActionCreateSerializer,
    FavoriteSerializer, FavoriteRestaurantSerializer,
    BlacklistSerializer, SwipeSessionSerializer, SwipeStatsSerializer
)


class SwipeActionViewSet(viewsets.ModelViewSet):
    """ViewSet for SwipeAction"""
    serializer_class = SwipeActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SwipeAction.objects.filter(user=self.request.user).select_related('dish', 'dish__cuisine')

    def get_serializer_class(self):
        if self.action == 'create':
            return SwipeActionCreateSerializer
        return SwipeActionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Check if already swiped
        dish_id = request.data.get('dish')
        if SwipeAction.objects.filter(user=request.user, dish_id=dish_id).exists():
            return Response(
                {"error": "You've already swiped on this dish"},
                status=status.HTTP_400_BAD_REQUEST
            )

        swipe = serializer.save()

        # Update current session if exists
        active_session = SwipeSession.objects.filter(
            user=request.user,
            ended_at__isnull=True
        ).first()

        if active_session:
            active_session.total_swipes += 1
            if swipe.direction == 'right':
                active_session.right_swipes += 1
            else:
                active_session.left_swipes += 1
            active_session.save()

        return Response(
            SwipeActionSerializer(swipe).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get swipe history"""
        direction = request.query_params.get('direction')
        queryset = self.get_queryset()

        if direction:
            queryset = queryset.filter(direction=direction)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet for Favorite dishes"""
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('dish', 'dish__cuisine')

    def create(self, request, *args, **kwargs):
        dish_id = request.data.get('dish_id')

        # Check if already favorited
        if Favorite.objects.filter(user=request.user, dish_id=dish_id).exists():
            return Response(
                {"error": "Dish already in favorites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle favorite status for a dish"""
        dish_id = request.data.get('dish_id')

        if not dish_id:
            return Response(
                {"error": "dish_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        favorite = Favorite.objects.filter(user=request.user, dish_id=dish_id).first()

        if favorite:
            favorite.delete()
            return Response({"status": "removed"}, status=status.HTTP_200_OK)
        else:
            favorite = Favorite.objects.create(user=request.user, dish_id=dish_id)
            return Response(
                {"status": "added", "favorite": FavoriteSerializer(favorite).data},
                status=status.HTTP_201_CREATED
            )


class FavoriteRestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for Favorite restaurants"""
    serializer_class = FavoriteRestaurantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteRestaurant.objects.filter(user=self.request.user).select_related('restaurant')

    def create(self, request, *args, **kwargs):
        restaurant_id = request.data.get('restaurant_id')

        if FavoriteRestaurant.objects.filter(user=request.user, restaurant_id=restaurant_id).exists():
            return Response(
                {"error": "Restaurant already in favorites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlacklistViewSet(viewsets.ModelViewSet):
    """ViewSet for Blacklist"""
    serializer_class = BlacklistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Blacklist.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SwipeSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for SwipeSession"""
    serializer_class = SwipeSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SwipeSession.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a new swipe session"""
        # End any active sessions
        SwipeSession.objects.filter(user=request.user, ended_at__isnull=True).update(
            ended_at=timezone.now()
        )

        session = SwipeSession.objects.create(
            user=request.user,
            cuisine_filter=request.data.get('cuisine_filter', ''),
            meal_type_filter=request.data.get('meal_type_filter', '')
        )

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def end(self, request):
        """End current swipe session"""
        session = SwipeSession.objects.filter(user=request.user, ended_at__isnull=True).first()

        if not session:
            return Response(
                {"error": "No active session found"},
                status=status.HTTP_404_NOT_FOUND
            )

        session.ended_at = timezone.now()
        session.save()

        serializer = self.get_serializer(session)
        return Response(serializer.data)


class SwipeStatsView(APIView):
    """Get user swipe statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get all swipes
        swipes = SwipeAction.objects.filter(user=user)
        total_swipes = swipes.count()
        right_swipes = swipes.filter(direction='right').count()
        left_swipes = swipes.filter(direction='left').count()

        match_rate = round((right_swipes / total_swipes * 100), 1) if total_swipes > 0 else 0

        # Favorite cuisines
        favorite_cuisines = swipes.filter(direction='right').values(
            'dish__cuisine__name', 'dish__cuisine__emoji'
        ).annotate(count=Count('id')).order_by('-count')[:5]

        # Most swiped meal type
        most_swiped_meal = swipes.values('dish__meal_type').annotate(
            count=Count('id')
        ).order_by('-count').first()

        most_swiped_meal_type = most_swiped_meal['dish__meal_type'] if most_swiped_meal else 'N/A'

        # Total favorites
        total_favorites = Favorite.objects.filter(user=user).count()

        # Total sessions
        total_sessions = SwipeSession.objects.filter(user=user).count()

        data = {
            'total_swipes': total_swipes,
            'right_swipes': right_swipes,
            'left_swipes': left_swipes,
            'match_rate': match_rate,
            'favorite_cuisines': list(favorite_cuisines),
            'most_swiped_meal_type': most_swiped_meal_type,
            'total_favorites': total_favorites,
            'total_sessions': total_sessions,
        }

        serializer = SwipeStatsSerializer(data)
        return Response(serializer.data)
