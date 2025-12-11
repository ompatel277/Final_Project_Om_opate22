from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from dishes.models import Cuisine, Dish, Restaurant, RestaurantDish


class DishDetailViewTests(TestCase):
    def setUp(self):
        patcher = patch("dishes.signal.fetch_dish_image_async.delay", autospec=True)
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.cuisine = Cuisine.objects.create(name="Italian")
        self.dish = Dish.objects.create(
            name="Pasta",
            description="Tasty",
            cuisine=self.cuisine,
            meal_type="dinner",
        )
        self.near_restaurant = Restaurant.objects.create(
            name="Near Resto",
            description="Near",
            address="123 Main St",
            city="Testville",
            state="TS",
            zip_code="00000",
            latitude=40.0,
            longitude=-75.0,
        )
        self.far_restaurant = Restaurant.objects.create(
            name="Far Resto",
            description="Far",
            address="456 Side St",
            city="Testville",
            state="TS",
            zip_code="11111",
            latitude=41.0,
            longitude=-76.0,
        )
        RestaurantDish.objects.create(restaurant=self.near_restaurant, dish=self.dish)
        RestaurantDish.objects.create(restaurant=self.far_restaurant, dish=self.dish)

    def test_dish_detail_view_resolves(self):
        response = self.client.get(reverse("dishes:dish_detail", args=[self.dish.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dish"], self.dish)

    def test_restaurants_sorted_by_distance_when_location_set(self):
        session = self.client.session
        session["user_location"] = {
            "latitude": 40.0,
            "longitude": -75.0,
            "city": "Testville",
        }
        session.save()

        response = self.client.get(reverse("dishes:dish_detail", args=[self.dish.id]))
        restaurants = list(response.context["restaurants"])

        self.assertGreater(len(restaurants), 0)
        self.assertEqual(restaurants[0].name, "Near Resto")
        # distance attribute should be present when location is set
        self.assertTrue(hasattr(restaurants[0], "distance"))
