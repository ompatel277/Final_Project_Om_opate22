"""
SerpApi Google Maps Service for finding restaurants
"""
from serpapi import GoogleSearch
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service to find restaurants using Google Maps via SerpApi"""

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY

    def search_restaurants(self, query, latitude, longitude, zoom=14, num_results=20):
        """
        Search for restaurants using Google Maps

        Args:
            query (str): Search query (e.g., "Pizza restaurants", "Sushi")
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            zoom (int): Map zoom level (default: 14)
            num_results (int): Maximum number of results to return

        Returns:
            list: List of restaurant data dictionaries
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return []

        try:
            params = {
                "engine": "google_maps",
                "q": query,
                "ll": f"@{latitude},{longitude},{zoom}z",
                "type": "search",
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            if "local_results" in results:
                return results["local_results"][:num_results]
            else:
                logger.warning(f"No restaurants found for query: {query}")
                return []

        except Exception as e:
            logger.error(f"Error searching restaurants for '{query}': {str(e)}")
            return []

    def search_restaurants_by_dish(self, dish_name, latitude, longitude, zoom=14, num_results=10):
        """
        Find restaurants that serve a specific dish

        Args:
            dish_name (str): Name of the dish
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            zoom (int): Map zoom level (default: 14)
            num_results (int): Maximum number of results

        Returns:
            list: List of restaurant data
        """
        query = f"{dish_name} restaurant"
        return self.search_restaurants(query, latitude, longitude, zoom, num_results)

    def get_place_details(self, data_id):
        """
        Get detailed information about a specific place

        Args:
            data_id (str): Google Maps data ID (e.g., "0x89c259a61c75684f:0x79d31adb123348d2")

        Returns:
            dict: Place details or None
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return None

        try:
            params = {
                "engine": "google_maps",
                "type": "place",
                "data": data_id,
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            return results.get("place_results")

        except Exception as e:
            logger.error(f"Error fetching place details for {data_id}: {str(e)}")
            return None

    def get_place_reviews(self, data_id, language="en", num_reviews=10):
        """
        Get reviews for a specific place

        Args:
            data_id (str): Google Maps data ID
            language (str): Language code (default: "en")
            num_reviews (int): Number of reviews to fetch

        Returns:
            list: List of reviews or empty list
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return []

        try:
            params = {
                "engine": "google_maps_reviews",
                "data_id": data_id,
                "hl": language,
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            reviews = results.get("reviews", [])
            return reviews[:num_reviews]

        except Exception as e:
            logger.error(f"Error fetching reviews for {data_id}: {str(e)}")
            return []

    def get_directions(self, start_addr, end_addr, travel_mode="driving"):
        """
        Get directions from start to end address

        Args:
            start_addr (str): Starting address or coordinates
            end_addr (str): Ending address or coordinates
            travel_mode (str): Mode of travel (driving, walking, bicycling, transit)

        Returns:
            dict: Directions data or None
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return None

        try:
            params = {
                "engine": "google_maps_directions",
                "start_addr": start_addr,
                "end_addr": end_addr,
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            return results.get("directions")

        except Exception as e:
            logger.error(f"Error getting directions: {str(e)}")
            return None

    def parse_restaurant_data(self, restaurant_data):
        """
        Parse raw Google Maps data into a clean dictionary

        Args:
            restaurant_data (dict): Raw restaurant data from Google Maps

        Returns:
            dict: Cleaned restaurant data
        """
        return {
            'name': restaurant_data.get('title'),
            'address': restaurant_data.get('address'),
            'phone': restaurant_data.get('phone'),
            'rating': restaurant_data.get('rating'),
            'reviews': restaurant_data.get('reviews'),
            'price_range': restaurant_data.get('price'),
            'latitude': restaurant_data.get('gps_coordinates', {}).get('latitude'),
            'longitude': restaurant_data.get('gps_coordinates', {}).get('longitude'),
            'google_place_id': restaurant_data.get('place_id'),
            'data_id': restaurant_data.get('data_id'),
            'website': restaurant_data.get('website'),
            'thumbnail': restaurant_data.get('thumbnail'),
            'type': restaurant_data.get('type'),
            'hours': restaurant_data.get('hours'),
            'service_options': restaurant_data.get('service_options', {}),
        }

    def save_restaurant_to_db(self, restaurant_data, dish=None):
        """
        Save restaurant to database

        Args:
            restaurant_data (dict): Raw restaurant data
            dish (Dish): Optional dish to associate with

        Returns:
            Restaurant: Created or updated restaurant
        """
        from .models import Restaurant, RestaurantDish

        parsed = self.parse_restaurant_data(restaurant_data)

        # Create or update restaurant
        restaurant, created = Restaurant.objects.update_or_create(
            google_place_id=parsed['google_place_id'],
            defaults={
                'name': parsed['name'],
                'address': parsed['address'] or '',
                'phone': parsed['phone'] or '',
                'website': parsed['website'] or '',
                'latitude': parsed['latitude'],
                'longitude': parsed['longitude'],
                'rating': parsed['rating'] or 0,
                'total_reviews': parsed['reviews'] or 0,
                'price_range': self._parse_price_range(parsed['price_range']),
                'is_active': True,
            }
        )

        # Associate with dish if provided
        if dish and restaurant:
            RestaurantDish.objects.get_or_create(
                restaurant=restaurant,
                dish=dish,
                defaults={'is_available': True}
            )

        return restaurant

    def _parse_price_range(self, price_str):
        """Convert price string ($, $$, $$$, $$$$) to choice"""
        if not price_str:
            return '$'

        price_map = {
            '$': '$',
            '$$': '$$',
            '$$$': '$$$',
            '$$$$': '$$$$'
        }
        return price_map.get(price_str, '$')
