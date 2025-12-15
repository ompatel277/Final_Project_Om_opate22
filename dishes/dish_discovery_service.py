"""
Live Dish Discovery Service using SerpApi
Fetches dishes dynamically using Google Search and Menu Highlights APIs
"""
from serpapi import GoogleSearch
from django.conf import settings
from django.db import transaction
import logging
import random

from .models import Dish, Cuisine, Restaurant, RestaurantDish
from .image_service import DishImageService

logger = logging.getLogger(__name__)

# Cuisine mapping for categorization
CUISINE_KEYWORDS = {
    'Italian': ['pasta', 'pizza', 'risotto', 'lasagna', 'ravioli', 'gnocchi', 'tiramisu', 'gelato', 'carbonara', 'bolognese'],
    'Mexican': ['taco', 'burrito', 'enchilada', 'quesadilla', 'guacamole', 'nachos', 'fajita', 'churro', 'tamale', 'salsa'],
    'Japanese': ['sushi', 'ramen', 'tempura', 'udon', 'sashimi', 'miso', 'teriyaki', 'mochi', 'edamame', 'gyoza'],
    'Indian': ['curry', 'tikka', 'masala', 'biryani', 'naan', 'samosa', 'tandoori', 'paneer', 'dal', 'chutney'],
    'Chinese': ['fried rice', 'dumpling', 'kung pao', 'lo mein', 'chow mein', 'spring roll', 'wonton', 'dim sum', 'orange chicken'],
    'Thai': ['pad thai', 'green curry', 'tom yum', 'satay', 'thai basil', 'massaman', 'papaya salad'],
    'American': ['burger', 'steak', 'bbq', 'wings', 'mac and cheese', 'hot dog', 'pancake', 'bacon', 'fries'],
    'Mediterranean': ['hummus', 'falafel', 'shawarma', 'gyro', 'kebab', 'pita', 'tzatziki', 'baklava'],
    'Korean': ['bibimbap', 'bulgogi', 'kimchi', 'korean bbq', 'japchae', 'tteokbokki', 'kimbap'],
    'French': ['croissant', 'crepe', 'souffle', 'quiche', 'baguette', 'eclair', 'ratatouille'],
}

# Meal type detection
MEAL_KEYWORDS = {
    'breakfast': ['pancake', 'waffle', 'egg', 'bacon', 'omelette', 'toast', 'cereal', 'bagel', 'croissant', 'breakfast'],
    'lunch': ['sandwich', 'salad', 'soup', 'wrap', 'burger', 'lunch'],
    'dinner': ['steak', 'pasta', 'curry', 'roast', 'grilled', 'dinner', 'entree'],
    'snack': ['fries', 'nachos', 'wings', 'chips', 'popcorn', 'pretzel'],
    'dessert': ['cake', 'ice cream', 'cookie', 'brownie', 'pie', 'chocolate', 'tiramisu', 'cheesecake', 'mochi', 'churro'],
}


class DishDiscoveryService:
    """Service to discover dishes using SerpApi Google Search and Menu Highlights"""

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.image_service = DishImageService()

    def discover_dishes_by_location(self, city, meal_type=None, cuisine_name=None, num_results=20):
        """
        Discover popular dishes near a location using Google Search

        Args:
            city: City name for location-based search
            meal_type: Optional filter (breakfast, lunch, dinner, snack, dessert)
            cuisine_name: Optional cuisine filter
            num_results: Number of dishes to return

        Returns:
            list: List of Dish objects (created or fetched from DB)
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured")
            return []

        # Build search query
        query_parts = ["popular dishes", "food"]
        if meal_type and meal_type != 'all':
            query_parts.insert(0, meal_type)
        if cuisine_name:
            query_parts.insert(0, cuisine_name)
        query_parts.append(f"near {city}")

        query = " ".join(query_parts)

        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": 30
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            dishes = []
            organic_results = results.get("organic_results", [])

            # Extract dish names from search results
            dish_names = self._extract_dish_names_from_results(organic_results, cuisine_name)

            # Create or get dishes from extracted names
            for dish_name in dish_names[:num_results]:
                dish = self._get_or_create_dish(dish_name, meal_type, cuisine_name)
                if dish:
                    dishes.append(dish)

            return dishes

        except Exception as e:
            logger.error(f"Error discovering dishes: {e}")
            return []

    def discover_dishes_from_restaurants(self, restaurant_names, city, num_results=20):
        """
        Discover dishes using Menu Highlights API from specific restaurants

        Args:
            restaurant_names: List of restaurant names to search
            city: City for context
            num_results: Max dishes to return

        Returns:
            list: List of Dish objects
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured")
            return []

        dishes = []

        for restaurant_name in restaurant_names[:10]:  # Limit API calls
            try:
                # Search for restaurant to get menu highlights
                params = {
                    "engine": "google",
                    "q": f"{restaurant_name} {city}",
                    "device": "desktop",
                    "api_key": self.api_key
                }

                search = GoogleSearch(params)
                results = search.get_dict()

                # Get menu highlights if available
                menu_highlights = results.get("menu_highlights", [])

                if menu_highlights:
                    for item in menu_highlights:
                        dish_name = item.get("title") or item.get("name")
                        if dish_name:
                            dish = self._get_or_create_dish(dish_name)
                            if dish and dish not in dishes:
                                dishes.append(dish)

                                if len(dishes) >= num_results:
                                    return dishes

            except Exception as e:
                logger.error(f"Error fetching menu for {restaurant_name}: {e}")
                continue

        return dishes

    def discover_dishes_for_cuisine(self, cuisine_name, city=None, meal_type=None, num_results=15):
        """
        Discover dishes for a specific cuisine type

        Args:
            cuisine_name: Name of cuisine (Italian, Mexican, etc.)
            city: Optional city for local results
            meal_type: Optional meal type filter
            num_results: Number of dishes to return

        Returns:
            list: List of Dish objects
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured")
            return []

        # Build query
        query = f"popular {cuisine_name} dishes"
        if meal_type and meal_type != 'all':
            query = f"popular {cuisine_name} {meal_type} dishes"
        if city:
            query += f" near {city}"

        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": 20
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            dishes = []
            organic_results = results.get("organic_results", [])

            # Extract dish names
            dish_names = self._extract_dish_names_from_results(organic_results, cuisine_name)

            # Create dishes
            for dish_name in dish_names[:num_results]:
                dish = self._get_or_create_dish(dish_name, meal_type, cuisine_name)
                if dish:
                    dishes.append(dish)

            return dishes

        except Exception as e:
            logger.error(f"Error discovering {cuisine_name} dishes: {e}")
            return []

    def search_dishes(self, query, city=None, num_results=10):
        """
        Search for specific dishes

        Args:
            query: Search query (dish name or type)
            city: Optional city for local context
            num_results: Number of results

        Returns:
            list: List of Dish objects
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured")
            return []

        search_query = f"{query} dish food"
        if city:
            search_query += f" near {city}"

        try:
            params = {
                "engine": "google",
                "q": search_query,
                "api_key": self.api_key,
                "num": 15
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            dishes = []
            organic_results = results.get("organic_results", [])

            dish_names = self._extract_dish_names_from_results(organic_results)

            for dish_name in dish_names[:num_results]:
                dish = self._get_or_create_dish(dish_name)
                if dish:
                    dishes.append(dish)

            return dishes

        except Exception as e:
            logger.error(f"Error searching dishes: {e}")
            return []

    def _extract_dish_names_from_results(self, organic_results, cuisine_hint=None):
        """Extract dish names from Google search results"""
        dish_names = set()

        # Common words to exclude
        exclude_words = {'restaurant', 'restaurants', 'menu', 'recipe', 'recipes',
                        'best', 'top', 'near', 'delivery', 'order', 'online',
                        'review', 'reviews', 'yelp', 'tripadvisor', 'doordash',
                        'ubereats', 'grubhub', 'food', 'foods', 'dishes'}

        for result in organic_results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            # Try to extract dish names from title
            # Look for patterns like "10 Best Pasta Dishes" or "Popular Thai Food"
            words = title.lower().split()

            # Check for known dish keywords
            all_keywords = []
            for cuisine_keywords in CUISINE_KEYWORDS.values():
                all_keywords.extend(cuisine_keywords)

            for keyword in all_keywords:
                if keyword.lower() in title.lower():
                    # Found a dish keyword, extract a proper name
                    dish_name = self._clean_dish_name(keyword, title)
                    if dish_name and len(dish_name) > 2:
                        dish_names.add(dish_name)

            # Also check snippet for dish mentions
            for keyword in all_keywords:
                if keyword.lower() in snippet.lower():
                    dish_name = self._clean_dish_name(keyword, snippet)
                    if dish_name and len(dish_name) > 2:
                        dish_names.add(dish_name)

        # If we have a cuisine hint, add some common dishes for that cuisine
        if cuisine_hint and cuisine_hint in CUISINE_KEYWORDS:
            for keyword in CUISINE_KEYWORDS[cuisine_hint][:5]:
                dish_names.add(keyword.title())

        return list(dish_names)

    def _clean_dish_name(self, keyword, context):
        """Clean and format a dish name"""
        # Capitalize properly
        name = keyword.title()

        # Handle multi-word dishes
        if ' ' in keyword:
            name = ' '.join(word.title() for word in keyword.split())

        return name

    def _get_or_create_dish(self, dish_name, meal_type=None, cuisine_name=None):
        """Get existing dish or create new one"""
        if not dish_name or len(dish_name) < 2:
            return None

        # Clean the dish name
        dish_name = dish_name.strip().title()

        # Check if dish already exists
        existing_dish = Dish.objects.filter(name__iexact=dish_name, is_active=True).first()
        if existing_dish:
            return existing_dish

        # Determine cuisine
        cuisine = None
        if cuisine_name:
            cuisine = Cuisine.objects.filter(name__iexact=cuisine_name).first()

        if not cuisine:
            cuisine = self._detect_cuisine(dish_name)

        # Determine meal type
        if not meal_type:
            meal_type = self._detect_meal_type(dish_name)

        # Determine dietary info
        is_vegetarian = self._is_vegetarian(dish_name)
        is_vegan = self._is_vegan(dish_name)

        # Get image URL
        image_url = self.image_service.get_best_dish_image(dish_name)

        try:
            with transaction.atomic():
                dish = Dish.objects.create(
                    name=dish_name,
                    description=f"Delicious {dish_name.lower()} - a popular dish discovered based on your location.",
                    cuisine=cuisine,
                    meal_type=meal_type or 'lunch',
                    is_vegetarian=is_vegetarian,
                    is_vegan=is_vegan,
                    image_url=image_url or '',
                    is_active=True,
                )
                logger.info(f"Created new dish: {dish_name}")
                return dish
        except Exception as e:
            logger.error(f"Error creating dish {dish_name}: {e}")
            return None

    def _detect_cuisine(self, dish_name):
        """Detect cuisine based on dish name"""
        dish_lower = dish_name.lower()

        for cuisine_name, keywords in CUISINE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in dish_lower:
                    cuisine = Cuisine.objects.filter(name__iexact=cuisine_name).first()
                    if cuisine:
                        return cuisine
                    # Create cuisine if it doesn't exist
                    cuisine, _ = Cuisine.objects.get_or_create(
                        name=cuisine_name,
                        defaults={'description': f'{cuisine_name} cuisine'}
                    )
                    return cuisine

        return None

    def _detect_meal_type(self, dish_name):
        """Detect meal type based on dish name"""
        dish_lower = dish_name.lower()

        for meal_type, keywords in MEAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in dish_lower:
                    return meal_type

        return 'lunch'  # Default

    def _is_vegetarian(self, dish_name):
        """Check if dish is likely vegetarian"""
        meat_keywords = ['chicken', 'beef', 'pork', 'lamb', 'fish', 'shrimp', 'bacon',
                        'steak', 'meat', 'sausage', 'ham', 'turkey', 'duck', 'seafood',
                        'crab', 'lobster', 'salmon', 'tuna']
        dish_lower = dish_name.lower()

        for keyword in meat_keywords:
            if keyword in dish_lower:
                return False

        veg_keywords = ['vegetable', 'veggie', 'tofu', 'paneer', 'cheese', 'mushroom',
                       'salad', 'vegetarian']
        for keyword in veg_keywords:
            if keyword in dish_lower:
                return True

        return False  # Unknown, default to non-vegetarian

    def _is_vegan(self, dish_name):
        """Check if dish is likely vegan"""
        non_vegan = ['cheese', 'cream', 'butter', 'egg', 'milk', 'honey', 'yogurt',
                    'chicken', 'beef', 'pork', 'fish', 'meat', 'paneer']
        dish_lower = dish_name.lower()

        for keyword in non_vegan:
            if keyword in dish_lower:
                return False

        vegan_keywords = ['vegan', 'plant-based', 'tofu']
        for keyword in vegan_keywords:
            if keyword in dish_lower:
                return True

        return False
