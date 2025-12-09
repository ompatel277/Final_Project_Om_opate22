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
            default=None,
            help='Maximum number of dishes to process (default: all dishes)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update images even if dish already has one'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API calls in seconds (default: 1.0)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        delay = options['delay']

        # Get dishes without images
        if force:
            dishes_query = Dish.objects.all()
        else:
            dishes_query = Dish.objects.filter(
                image='',
                image_url=''
            )

        # Apply limit if specified
        if limit:
            dishes = dishes_query[:limit]
            total_count = min(limit, dishes_query.count())
        else:
            dishes = dishes_query
            total_count = dishes.count()

        if not dishes:
            self.stdout.write(self.style.SUCCESS('No dishes to process!'))
            return

        self.stdout.write(f'Processing {total_count} dishes...')
        self.stdout.write(f'API delay: {delay} seconds between requests\n')

        service = DishImageService()
        updated = 0
        failed = 0

        for index, dish in enumerate(dishes, 1):
            # Progress indicator
            self.stdout.write(f'[{index}/{total_count}] Fetching image for: {dish.name}')

            try:
                image_url = service.get_best_dish_image(dish.name)

                if image_url:
                    dish.image_url = image_url
                    dish.save()
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Updated: {image_url[:60]}...')
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ✗ No image found')
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )

            # Rate limiting - be nice to the API
            if index < total_count:  # Don't delay after the last request
                time.sleep(delay)

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Successfully updated: {updated} dishes')
        )
        if failed > 0:
            self.stdout.write(
                self.style.WARNING(f'✗ Failed: {failed} dishes')
            )
        self.stdout.write('='*60)
