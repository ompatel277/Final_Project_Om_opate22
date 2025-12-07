from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin
from .models import Cuisine, Dish, Restaurant, RestaurantDish
from .serializers import (
    CuisineSerializer, DishSerializer, DishCardSerializer,
    RestaurantSerializer, RestaurantWithDistanceSerializer
)


class CuisineViewSet(viewsets.ModelViewSet):
    """ViewSet for Cuisine"""
    queryset = Cuisine.objects.all()
    serializer_class = CuisineSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']


class DishViewSet(viewsets.ModelViewSet):
    """ViewSet for Dish"""
    queryset = Dish.objects.filter(is_active=True).select_related('cuisine').prefetch_related('ingredients')
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'cuisine': ['exact'],
        'meal_type': ['exact'],
        'is_vegetarian': ['exact'],
        'is_vegan': ['exact'],
        'is_gluten_free': ['exact'],
        'spice_level': ['exact', 'lte', 'gte'],
        'calories': ['lte', 'gte'],
    }
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'average_rating', 'total_swipes', 'calories', 'created_at']
    ordering = ['-average_rating']

    def get_serializer_class(self):
        if self.action == 'swipe_feed':
            return DishCardSerializer
        return DishSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def swipe_feed(self, request):
        """Get personalized swipe feed for user"""
        user = request.user
        profile = user.profile

        # Get dishes user hasn't swiped on yet
        from swipes.models import SwipeAction
        swiped_dish_ids = SwipeAction.objects.filter(user=user).values_list('dish_id', flat=True)

        queryset = self.get_queryset().exclude(id__in=swiped_dish_ids)

        # Filter based on user preferences
        if profile.diet_type == 'vegetarian':
            queryset = queryset.filter(is_vegetarian=True)
        elif profile.diet_type == 'vegan':
            queryset = queryset.filter(is_vegan=True)

        # Filter by allergies
        allergies = profile.get_allergies_list()
        if allergies:
            from .models import DishIngredient
            allergen_dish_ids = DishIngredient.objects.filter(
                is_allergen=True,
                name__in=allergies
            ).values_list('dish_id', flat=True)
            queryset = queryset.exclude(id__in=allergen_dish_ids)

        # Filter by blacklist
        from swipes.models import Blacklist
        blacklisted_dish_ids = Blacklist.objects.filter(
            user=user,
            blacklist_type='dish'
        ).values_list('dish_id', flat=True)
        queryset = queryset.exclude(id__in=blacklisted_dish_ids)

        # Apply filters from query params
        meal_type = request.query_params.get('meal_type')
        if meal_type:
            queryset = queryset.filter(meal_type=meal_type)

        cuisine = request.query_params.get('cuisine')
        if cuisine:
            queryset = queryset.filter(cuisine_id=cuisine)

        # Randomize and limit
        queryset = queryset.order_by('?')[:50]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Get similar dishes"""
        dish = self.get_object()
        similar_dishes = Dish.objects.filter(
            cuisine=dish.cuisine,
            meal_type=dish.meal_type,
            is_active=True
        ).exclude(id=dish.id).order_by('-average_rating')[:10]

        serializer = DishCardSerializer(similar_dishes, many=True)
        return Response(serializer.data)


class RestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for Restaurant"""
    queryset = Restaurant.objects.filter(is_active=True).select_related('cuisine_type')
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'city': ['exact', 'icontains'],
        'price_range': ['exact'],
        'cuisine_type': ['exact'],
        'rating': ['gte'],
        'has_uber_eats': ['exact'],
        'has_doordash': ['exact'],
        'has_grubhub': ['exact'],
    }
    search_fields = ['name', 'description', 'address', 'city']
    ordering_fields = ['name', 'rating', 'price_range']
    ordering = ['-rating']

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get nearby restaurants based on user location"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', 5))  # miles

        if not lat or not lng:
            return Response(
                {"error": "Latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        lat = float(lat)
        lng = float(lng)

        # Haversine formula for distance calculation
        # Distance in miles
        queryset = self.get_queryset().filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).annotate(
            distance=ExpressionWrapper(
                3959 * ACos(
                    Cos(Radians(lat)) * Cos(Radians(F('latitude'))) *
                    Cos(Radians(F('longitude')) - Radians(lng)) +
                    Sin(Radians(lat)) * Sin(Radians(F('latitude')))
                ),
                output_field=FloatField()
            )
        ).filter(distance__lte=radius).order_by('distance')

        serializer = RestaurantWithDistanceSerializer(queryset, many=True)
        return Response(serializer.data)


class DishRestaurantsView(APIView):
    """Get restaurants serving a specific dish"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
        except Dish.DoesNotExist:
            return Response(
                {"error": "Dish not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get user location if provided
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        max_distance = float(request.query_params.get('max_distance', 10))

        restaurant_dishes = RestaurantDish.objects.filter(
            dish=dish,
            is_available=True,
            restaurant__is_active=True
        ).select_related('restaurant', 'restaurant__cuisine_type')

        restaurants_data = []

        for rd in restaurant_dishes:
            restaurant = rd.restaurant
            data = RestaurantSerializer(restaurant).data
            data['dish_price'] = rd.price

            # Calculate distance if coordinates provided
            if lat and lng and restaurant.latitude and restaurant.longitude:
                from math import radians, cos, sin, acos
                lat1 = radians(float(lat))
                lng1 = radians(float(lng))
                lat2 = radians(restaurant.latitude)
                lng2 = radians(restaurant.longitude)

                distance = 3959 * acos(
                    cos(lat1) * cos(lat2) * cos(lng2 - lng1) + sin(lat1) * sin(lat2)
                )

                if distance <= max_distance:
                    data['distance'] = round(distance, 2)
                    data['estimated_delivery_time'] = int(distance * 8)  # ~8 min per mile
                    restaurants_data.append(data)
            else:
                data['distance'] = None
                data['estimated_delivery_time'] = None
                restaurants_data.append(data)

        # Sort by distance if available
        if lat and lng:
            restaurants_data.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))

        return Response({
            'dish': DishSerializer(dish).data,
            'restaurants': restaurants_data,
            'total_count': len(restaurants_data)
        })
