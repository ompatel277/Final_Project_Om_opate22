"""
Management command to find restaurants for dishes using Google Maps
"""
from django.core.management.base import BaseCommand
from dishes.models import Dish, Restaurant, RestaurantDish, Cuisine
from dishes.maps_service import GoogleMapsService
import time


class Command(BaseCommand):
    help = 'Find restaurants for dishes using Google Maps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dish',
            type=str,
            help='Specific dish name to search for'
        )
        parser.add_argument(
            '--latitude',
            type=float,
            default=40.7455096,
            help='Latitude coordinate (default: NYC)'
        )
        parser.add_argument(
            '--longitude',
            type=float,
            default=-74.0083012,
            help='Longitude coordinate (default: NYC)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of dishes to process'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API calls in seconds (default: 1.0)'
        )

    def handle(self, *args, **options):
        dish_name = options['dish']
        latitude = options['latitude']
        longitude = options['longitude']
        limit = options['limit']
        delay = options['delay']

        service = GoogleMapsService()

        if dish_name:
            # Search for specific dish
            self.search_for_dish(dish_name, service, latitude, longitude)
        else:
            # Search for multiple dishes
            dishes = Dish.objects.all()[:limit]
            total = min(limit, Dish.objects.count())

            self.stdout.write(f'Searching restaurants for {total} dishes...')
            self.stdout.write(f'Location: ({latitude}, {longitude})')
            self.stdout.write(f'API delay: {delay} seconds\n')

            for index, dish in enumerate(dishes, 1):
                self.stdout.write(f'[{index}/{total}] Searching for: {dish.name}')

                try:
                    restaurants = service.search_restaurants_by_dish(
                        dish.name,
                        latitude,
                        longitude,
                        num_results=5
                    )

                    if restaurants:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Found {len(restaurants)} restaurants')
                        )

                        # Display first 3 results
                        for i, restaurant in enumerate(restaurants[:3], 1):
                            parsed = service.parse_restaurant_data(restaurant)
                            self.stdout.write(
                                f"    {i}. {parsed['name']} - {parsed['rating']}⭐ ({parsed['reviews']} reviews)"
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ✗ No restaurants found')
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error: {str(e)}')
                    )

                # Rate limiting
                if index < total:
                    time.sleep(delay)

            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('✓ Search complete'))
            self.stdout.write('=' * 60)

    def search_for_dish(self, dish_name, service, latitude, longitude):
        """Search restaurants for a specific dish"""
        self.stdout.write(f'Searching for restaurants serving: {dish_name}')
        self.stdout.write(f'Location: ({latitude}, {longitude})\n')

        try:
            restaurants = service.search_restaurants_by_dish(
                dish_name,
                latitude,
                longitude,
                num_results=20
            )

            if restaurants:
                self.stdout.write(
                    self.style.SUCCESS(f'Found {len(restaurants)} restaurants!\n')
                )

                for i, restaurant in enumerate(restaurants, 1):
                    parsed = service.parse_restaurant_data(restaurant)

                    self.stdout.write('─' * 60)
                    self.stdout.write(f"{i}. {parsed['name']}")
                    self.stdout.write(f"   Address: {parsed['address']}")
                    self.stdout.write(f"   Rating: {parsed['rating']}⭐ ({parsed['reviews']} reviews)")
                    self.stdout.write(f"   Price: {parsed['price_range']}")
                    if parsed['phone']:
                        self.stdout.write(f"   Phone: {parsed['phone']}")
                    if parsed['website']:
                        self.stdout.write(f"   Website: {parsed['website']}")
                    self.stdout.write('')

            else:
                self.stdout.write(
                    self.style.WARNING('No restaurants found')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
