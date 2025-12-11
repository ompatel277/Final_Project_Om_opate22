"""
Management command to find restaurants for dishes using Google Maps
and populate RestaurantDish relationships.

Usage examples:
  python manage.py find_restaurants --dish "Pad Thai" --latitude 40.74 --longitude -74.00 --limit 20
  python manage.py find_restaurants --limit 10
"""
import time
from django.core.management.base import BaseCommand
from django.db import transaction

from dishes.models import Dish, RestaurantDish
from dishes.maps_service import GoogleMapsService


class Command(BaseCommand):
    help = "Find restaurants for dishes using Google Maps and populate RestaurantDish"

    def add_arguments(self, parser):
        parser.add_argument("--dish", type=str, help="Specific dish name to search for")
        parser.add_argument("--latitude", type=float, default=40.7455096, help="Latitude (default: NYC)")
        parser.add_argument("--longitude", type=float, default=-74.0083012, help="Longitude (default: NYC)")
        parser.add_argument("--limit", type=int, default=10, help="Maximum number of dishes to process")
        parser.add_argument("--per-dish", type=int, default=5, help="Max restaurants to fetch per dish")
        parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls in seconds")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="If set, do not save anything to DB (prints what would happen)",
        )

    def handle(self, *args, **options):
        dish_name = options["dish"]
        latitude = options["latitude"]
        longitude = options["longitude"]
        limit = options["limit"]
        per_dish = options["per_dish"]
        delay = options["delay"]
        dry_run = options["dry_run"]

        service = GoogleMapsService()

        if dish_name:
            dish = Dish.objects.filter(name__iexact=dish_name).first()
            if not dish:
                self.stdout.write(self.style.ERROR(f'No Dish found with name "{dish_name}"'))
                return
            self._populate_for_one_dish(service, dish, latitude, longitude, per_dish, delay, dry_run)
            return

        dishes = list(Dish.objects.all()[:limit])
        total = len(dishes)

        if total == 0:
            self.stdout.write(self.style.WARNING("No dishes found in database."))
            return

        self.stdout.write(f"Populating restaurants for {total} dishes...")
        self.stdout.write(f"Location: ({latitude}, {longitude}) | per_dish={per_dish} | delay={delay}s")
        self.stdout.write(f"Dry run: {dry_run}\n")

        for idx, dish in enumerate(dishes, 1):
            self.stdout.write(f"[{idx}/{total}] Dish: {dish.name}")
            self._populate_for_one_dish(service, dish, latitude, longitude, per_dish, delay, dry_run)

            if idx < total and delay > 0:
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS("\n✓ Done populating RestaurantDish relationships."))

    def _populate_for_one_dish(self, service, dish, latitude, longitude, per_dish, delay, dry_run):
        try:
            results = service.search_restaurants_by_dish(
                dish.name,
                latitude,
                longitude,
                num_results=per_dish,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ API error: {e}"))
            return

        if not results:
            self.stdout.write(self.style.WARNING("  ✗ No restaurants found"))
            return

        self.stdout.write(self.style.SUCCESS(f"  ✓ Found {len(results)} restaurants"))

        created_links = 0
        updated_links = 0

        for r in results:
            parsed = service.parse_restaurant_data(r)

            # Save restaurant + link to dish using existing service method
            if dry_run:
                self.stdout.write(
                    f"    - Would save: {parsed.get('name')} | rating={parsed.get('rating')} | reviews={parsed.get('reviews')}"
                )
                continue

            with transaction.atomic():
                restaurant = service.save_restaurant_to_db(r, dish=dish)
                if not restaurant:
                    self.stdout.write(self.style.WARNING(f"    - Skipped restaurant (missing place id): {parsed.get('name')}"))
                    continue

                # Ensure RestaurantDish exists and is available
                link, created = RestaurantDish.objects.update_or_create(
                    restaurant=restaurant,
                    dish=dish,
                    defaults={
                        "is_available": True,
                        # keep price as-is if you have it; otherwise default 0
                        "price": getattr(link := None, "price", 0) if False else 0
                    },
                )

                if created:
                    created_links += 1
                else:
                    updated_links += 1

                self.stdout.write(f"    ✓ Linked: {restaurant.name}")

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Links created: {created_links}, updated: {updated_links}")
            )
