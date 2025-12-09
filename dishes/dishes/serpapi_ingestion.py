"""Bridge SerpAPI results into our local models."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction

from integrations.serpapi import SerpApiClient
from .models import Cuisine, Dish, Restaurant, RestaurantDish


logger = logging.getLogger(__name__)


def _get_default_cuisine() -> Cuisine:
    cuisine, _ = Cuisine.objects.get_or_create(name="International", defaults={"emoji": "🌎"})
    return cuisine


def _map_price_level(price_level: Optional[str]) -> str:
    if not price_level:
        return "$$"
    if isinstance(price_level, str) and price_level.startswith("$"):
        return price_level[:4]
    try:
        level = int(price_level)
        return "$" * max(1, min(level, 4))
    except Exception:
        return "$$"


def ingest_nearby_restaurants_and_dishes(
    latitude: float,
    longitude: float,
    query: str = "restaurants",
    desired_dish_count: int = 25,
    cuisine_keyword: Optional[str] = None,
) -> int:
    """Pull real restaurant/menu data near the user and hydrate local tables.

    Returns the number of new dishes created (used by swipe feed to stay fresh).
    """

    client = SerpApiClient()
    if not client.is_configured():
        return 0

    search_query = f"{cuisine_keyword} restaurants" if cuisine_keyword else query
    results = client.search_restaurants(latitude, longitude, query=search_query)

    if not results:
        return 0

    created_dishes = 0
    default_cuisine = _get_default_cuisine()

    for place in results:
        place_id = place.get("place_id") or place.get("data_id")
        if not place_id:
            continue

        restaurant, _ = Restaurant.objects.get_or_create(
            google_place_id=place_id,
            defaults={
                "name": place.get("title") or place.get("name", "Unnamed Restaurant"),
                "address": place.get("address", ""),
                "city": place.get("address", "").split(",")[0] if place.get("address") else "",
                "state": "",
                "zip_code": "",
                "latitude": place.get("gps_coordinates", {}).get("latitude"),
                "longitude": place.get("gps_coordinates", {}).get("longitude"),
                "price_range": _map_price_level(place.get("price")),
                "rating": place.get("rating") or 0.0,
                "total_reviews": place.get("user_ratings_total") or 0,
            },
        )

        # Update dynamic fields if we already had the restaurant
        restaurant.rating = place.get("rating") or restaurant.rating
        restaurant.total_reviews = place.get("user_ratings_total") or restaurant.total_reviews
        gps = place.get("gps_coordinates") or {}
        restaurant.latitude = gps.get("latitude") or restaurant.latitude
        restaurant.longitude = gps.get("longitude") or restaurant.longitude
        if cuisine_keyword and not restaurant.cuisine_type:
            restaurant.cuisine_type = default_cuisine
        restaurant.save()

        details = client.get_place_details(place_id)
        menu_items: Iterable = details.get("menu_items") or []

        # Fall back to a single featured dish when no menu is exposed
        if not menu_items:
            primary_title = place.get("title") or restaurant.name
            menu_items = [
                {
                    "name": f"Popular at {primary_title}",
                    "description": details.get("about_this_place", "Real menu item"),
                    "price": place.get("price"),
                }
            ]

        with transaction.atomic():
            for item in menu_items:
                if created_dishes >= desired_dish_count:
                    break

                dish_name = str(item.get("name") or "House Special")[:200]
                description = item.get("description") or details.get("about_this_place") or "Menu item"
                price_raw = item.get("price") or place.get("price") or "0"

                dish, _ = Dish.objects.get_or_create(
                    name=dish_name,
                    defaults={
                        "description": description,
                        "cuisine": restaurant.cuisine_type or default_cuisine,
                        "meal_type": "dinner",
                        "image_url": (item.get("thumbnail") or place.get("thumbnail")),
                    },
                )

                try:
                    price_value = Decimal(str(price_raw).replace("$", ""))
                except Exception:
                    price_value = Decimal("0.00")

                RestaurantDish.objects.get_or_create(
                    restaurant=restaurant,
                    dish=dish,
                    defaults={"price": price_value or Decimal("0.00")},
                )
                created_dishes += 1

        if created_dishes >= desired_dish_count:
            break

    logger.info("Hydrated %s dishes from SerpAPI", created_dishes)
    return created_dishes
