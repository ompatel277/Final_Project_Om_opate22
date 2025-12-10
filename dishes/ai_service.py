from serpapi import GoogleSearch
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered features using SerpAPI"""

    def __init__(self):
        self.api_key = "60d17e68d90a8a956e867f1b697bba1f2e6213197b807232413e21a3a6100d2e"

    def get_dish_description(self, dish_name, cuisine_name=None):
        """Get AI-generated description for a dish"""
        try:
            query = f"{dish_name}"
            if cuisine_name:
                query += f" {cuisine_name} cuisine"

            params = {
                "engine": "google_ai_mode",
                "q": f"Describe {query} dish in detail, including taste, ingredients, and preparation",
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            if "text_blocks" in results and results["text_blocks"]:
                # Combine text blocks into a description
                description = " ".join(results["text_blocks"][:3])  # First 3 blocks
                return description[:500]  # Limit to 500 chars

            return None
        except Exception as e:
            logger.error(f"Error getting AI description: {e}")
            return None

    def get_dish_info(self, dish_name):
        """Get additional info about a dish using Google Search"""
        try:
            params = {
                "engine": "google",
                "q": f"{dish_name} recipe ingredients",
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            info = {
                'description': None,
                'ingredients': [],
                'origin': None
            }

            if "organic_results" in results and results["organic_results"]:
                first_result = results["organic_results"][0]
                info['description'] = first_result.get('snippet', '')

            return info
        except Exception as e:
            logger.error(f"Error getting dish info: {e}")
            return None

    def chat_response(self, user_message, context=None):
        """Get AI chatbot response"""
        try:
            query = user_message
            if context:
                query = f"Context: {context}. Question: {user_message}"

            params = {
                "engine": "google_ai_mode",
                "q": query,
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            if "text_blocks" in results and results["text_blocks"]:
                return " ".join(results["text_blocks"][:2])

            return "I'm not sure about that. Can you ask something else?"
        except Exception as e:
            logger.error(f"Error getting chat response: {e}")
            return "Sorry, I'm having trouble responding right now."


class DeliveryAppService:
    """Service to get delivery app links for restaurants"""

    @staticmethod
    def get_delivery_links(restaurant_name, address):
        """Generate delivery app links"""
        links = {}

        # Encode for URLs
        from urllib.parse import quote
        name_encoded = quote(restaurant_name)
        address_encoded = quote(address)

        # Uber Eats
        links['uber_eats'] = f"https://www.ubereats.com/search?q={name_encoded}"

        # DoorDash
        links['doordash'] = f"https://www.doordash.com/search/store/{name_encoded}"

        # Grubhub
        links['grubhub'] = f"https://www.grubhub.com/search?searchTerm={name_encoded}"

        # Postmates
        links['postmates'] = f"https://postmates.com/search/{name_encoded}"

        return links
