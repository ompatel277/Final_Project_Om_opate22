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

    # ---------------------------
    # SEARCH (FAST LIST PAGE)
    # ---------------------------
    def search_restaurants(self, query, latitude, longitude, zoom=14, num_results=20):
        """
        Search for restaurants using Google Maps

        Returns:
            list: List of restaurant data dictionaries from SerpApi local_results
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

            local_results = results.get("local_results", [])
            if not local_results:
                logger.warning(f"No restaurants found for query: {query}")
                return []

            return local_results[:num_results]

        except Exception as e:
            logger.error(f"Error searching restaurants for '{query}': {str(e)}")
            return []

    def search_restaurants_by_dish(self, dish_name, latitude, longitude, zoom=14, num_results=10):
        """Find restaurants that serve a specific dish"""
        query = f"{dish_name} restaurant"
        return self.search_restaurants(query, latitude, longitude, zoom, num_results)

    # ---------------------------
    # DETAILS (ONLY WHEN NEEDED)
    # ---------------------------
    def get_place_details(self, data_id):
        """
        Get detailed information about a specific place (SerpApi "place" type).

        Args:
            data_id (str): Google Maps data_id from local_results

        Returns:
            dict: place_results or None
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return None

        if not data_id:
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
        Get reviews for a specific place.

        Args:
            data_id (str): Google Maps data_id
        Returns:
            list: review dicts
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return []

        if not data_id:
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

    def get_details_and_reviews(self, data_id, language="en", num_reviews=10):
        """
        Convenience helper for detail pages.
        Fetches place details + reviews in one call chain.

        Returns:
            tuple: (place_details_dict_or_None, reviews_list)
        """
        details = self.get_place_details(data_id)
        reviews = self.get_place_reviews(data_id, language=language, num_reviews=num_reviews)
        return details, reviews

    # ---------------------------
    # DIRECTIONS
    # ---------------------------
    def get_directions(self, start_addr, end_addr, travel_mode="driving"):
        """Get directions from start to end address"""
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

    # ---------------------------
    # PARSING
    # ---------------------------
    def parse_restaurant_data(self, restaurant_data):
        """Parse raw local_results restaurant data into a clean dictionary"""
        return {
            'name': restaurant_data.get('title'),
            'address': restaurant_data.get('address'),
            'phone': restaurant_data.get('phone'),
            'rating': restaurant_data.get('rating'),
            'reviews': restaurant_data.get('reviews'),  # this is usually COUNT, not review text
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

    # ---------------------------
    # DATABASE SAVE (STORE IDS + PHOTO)
    # ---------------------------
    def save_restaurant_to_db(self, restaurant_data, dish=None):
        """
        Save restaurant to database.
        IMPORTANT: stores data_id + thumbnail so detail page can fetch reviews/details and show photo.
        """
        from .models import Restaurant, RestaurantDish

        # Check if data is already parsed or raw
        if isinstance(restaurant_data, dict) and 'title' in restaurant_data:
            parsed = self.parse_restaurant_data(restaurant_data)
        else:
            parsed = restaurant_data or {}

        # Skip if no google_place_id (required for uniqueness)
        if not parsed.get('google_place_id'):
            logger.warning(f"Skipping restaurant {parsed.get('name')} - no google_place_id")
            return None

        # Parse city/state/zip from address
        city, state, zip_code = self._parse_address_parts(parsed.get('address', ''))

        # Create or update restaurant
        try:
            restaurant, created = Restaurant.objects.update_or_create(
                google_place_id=parsed['google_place_id'],
                defaults={
                    'name': parsed.get('name') or 'Unknown Restaurant',
                    'address': parsed.get('address') or '',
                    'city': city,
                    'state': state,
                    'zip_code': zip_code,
                    'phone': parsed.get('phone') or '',
                    'website': parsed.get('website') or '',
                    'latitude': parsed.get('latitude'),
                    'longitude': parsed.get('longitude'),
                    'rating': parsed.get('rating') or 0,
                    'total_reviews': parsed.get('reviews') or 0,
                    'price_range': self._parse_price_range(parsed.get('price_range')),
                    'is_active': True,

                    # ✅ NEW: persist identifiers and photo for later detail-page hydration
                    'data_id': parsed.get('data_id') or '',
                    'thumbnail': parsed.get('thumbnail') or '',
                }
            )

            # Associate with dish if provided
            if dish and restaurant:
                RestaurantDish.objects.get_or_create(
                    restaurant=restaurant,
                    dish=dish,
                    defaults={'is_available': True, 'price': 0}
                )

            return restaurant

        except Exception as e:
            logger.error(f"Error saving restaurant {parsed.get('name')}: {str(e)}")
            return None

    # ---------------------------
    # HELPERS
    # ---------------------------
    def _parse_address_parts(self, address):
        """Parse city, state, and zip from a full address string"""
        if not address:
            return ('Unknown', 'Unknown', '')

        import re

        state_zip_pattern = r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})?'
        match = re.search(state_zip_pattern, address)

        if match:
            city = match.group(1).strip()
            state = match.group(2).strip()
            zip_code = match.group(3) or ''
            return (city, state, zip_code)

        parts = address.split(',')
        if len(parts) >= 3:
            city = parts[-2].strip()
            last_part = parts[-1].strip()
            state_match = re.match(r'([A-Z]{2})', last_part)
            state = state_match.group(1) if state_match else last_part[:20]
            zip_match = re.search(r'(\d{5})', last_part)
            zip_code = zip_match.group(1) if zip_match else ''
            return (city[:100], state[:50], zip_code)
        elif len(parts) == 2:
            return (parts[0].strip()[:100], parts[1].strip()[:50], '')
        else:
            return (address[:100], 'Unknown', '')

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
