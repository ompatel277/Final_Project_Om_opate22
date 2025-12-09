from celery import shared_task
from .models import Dish
from .image_service import DishImageService
import logging

logger = logging.getLogger(__name__)


@shared_task
def fetch_dish_image_async(dish_id):
    """
    Asynchronously fetch an image for a dish

    Args:
        dish_id: The ID of the dish to fetch an image for
    """
    try:
        dish = Dish.objects.get(pk=dish_id)

        if not dish.image and not dish.image_url:
            service = DishImageService()
            image_url = service.get_best_dish_image(dish.name)

            if image_url:
                Dish.objects.filter(pk=dish.pk).update(image_url=image_url)
                logger.info(f"✓ Async: Successfully fetched image for: {dish.name}")
            else:
                logger.warning(f"✗ Async: No image found for: {dish.name}")

    except Dish.DoesNotExist:
        logger.error(f"Dish with ID {dish_id} does not exist")
    except Exception as e:
        logger.error(f"Error in async image fetch: {str(e)}")
