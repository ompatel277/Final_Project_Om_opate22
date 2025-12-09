from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Dish
from .tasks import fetch_dish_image_async
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Dish)
def fetch_dish_image(sender, instance, created, **kwargs):
    """Queue an async task to fetch image for new dishes"""
    if not instance.image and not instance.image_url:
        logger.info(f"Queuing async image fetch for: {instance.name}")
        # Run in background with Celery
        fetch_dish_image_async.delay(instance.pk)
