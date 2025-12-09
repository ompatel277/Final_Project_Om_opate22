"""
Management command to fetch images for dishes without images
"""
from django.core.management.base import BaseCommand
from dishes.models import Dish
from dishes.image_service import DishImageService
import time


class Command(BaseCommand):
    help = 'Fetch images for dishes that don\'t have images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of dishes to process'
        )

    def handle(self, *args, **options):
        limit = options['limit']

        # Get dishes without images
        dishes = Dish.objects.filter(
            image='',
            image_url=''
        )[:limit]

        if not dishes:
            self.stdout.write(self.style.SUCCESS('All dishes have images!'))
            return

        self.stdout.write(f'Found {dishes.count()} dishes without images')

        service = DishImageService()
        updated = 0

        for dish in dishes:
            self.stdout.write(f'Fetching image for: {dish.name}')

            image_url = service.get_best_dish_image(dish.name)

            if image_url:
                dish.image_url = image_url
                dish.save()
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Updated {dish.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'✗ No image found for {dish.name}')
                )

            # Be nice to the API - add delay
            time.sleep(1)

        self.stdout.write(
            self.style.SUCCESS(f'\nUpdated {updated} out of {dishes.count()} dishes')
        )
