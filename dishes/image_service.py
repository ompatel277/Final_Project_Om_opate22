"""
SerpApi Image Search Service for fetching dish images
"""
from serpapi import GoogleSearch
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DishImageService:
    """Service to fetch dish images from Google using SerpApi"""

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY

    def search_dish_images(self, dish_name, num_results=10):
        """
        Search for dish images using SerpApi

        Args:
            dish_name (str): Name of the dish to search for
            num_results (int): Number of images to return

        Returns:
            list: List of image data dictionaries
        """
        if not self.api_key:
            logger.error("SERPAPI_KEY not configured in settings")
            return []

        try:
            params = {
                "engine": "google_images_light",
                "q": f"{dish_name} food",
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            if "images_results" in results:
                return results["images_results"][:num_results]
            else:
                logger.warning(f"No images found for dish: {dish_name}")
                return []

        except Exception as e:
            logger.error(f"Error fetching images for {dish_name}: {str(e)}")
            return []

    def get_best_dish_image(self, dish_name):
        """
        Get the best (first) image URL for a dish

        Args:
            dish_name (str): Name of the dish

        Returns:
            str: Image URL or None
        """
        images = self.search_dish_images(dish_name, num_results=1)
        if images and len(images) > 0:
            return images[0].get('image')
        return None

    def get_all_image_urls(self, dish_name, num_results=10):
        """
        Get all image URLs for a dish

        Args:
            dish_name (str): Name of the dish
            num_results (int): Number of images to fetch

        Returns:
            list: List of image URLs
        """
        images = self.search_dish_images(dish_name, num_results)
        return [img.get('image') for img in images if img.get('image')]
