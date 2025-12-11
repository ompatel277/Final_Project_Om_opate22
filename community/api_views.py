from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import Avg
from .models import Review, ReviewHelpful, TrendingDish
from .serializers import ReviewSerializer, TrendingDishSerializer


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


