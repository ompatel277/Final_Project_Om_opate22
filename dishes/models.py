from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Cuisine(models.Model):
    """Cuisine types for categorizing dishes"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=10, default="🍽️")

    def __str__(self):
        return f"{self.emoji} {self.name}"

    class Meta:
        ordering = ['name']


class Dish(models.Model):
    """Main dish model"""

    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
        ('dessert', 'Dessert'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    cuisine = models.ForeignKey(Cuisine, on_delete=models.SET_NULL, null=True, related_name='dishes')

    # Nutritional Information
    calories = models.IntegerField(null=True, blank=True)
    protein = models.IntegerField(null=True, blank=True, help_text="grams")
    carbs = models.IntegerField(null=True, blank=True, help_text="grams")
    fat = models.IntegerField(null=True, blank=True, help_text="grams")

    # Dish Details
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    spice_level = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="0=Not Spicy, 5=Very Spicy"
    )

    # Media
    image = models.ImageField(upload_to='dishes/', null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True)

    # Ratings and Stats
    average_rating = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)
    total_swipes = models.IntegerField(default=0)
    total_right_swipes = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def match_rate(self):
        """Calculate percentage of right swipes"""
        if self.total_swipes == 0:
            return 0
        return round((self.total_right_swipes / self.total_swipes) * 100, 1)

    @property
    def display_image(self):
        """Return image or placeholder"""
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return '/static/images/placeholder-dish.jpg'

    class Meta:
        verbose_name = "Dish"
        verbose_name_plural = "Dishes"
        ordering = ['-created_at']


class Restaurant(models.Model):
    """Restaurant model"""

    PRICE_RANGE_CHOICES = [
        ('$', 'Budget ($)'),
        ('$$', 'Moderate ($$)'),
        ('$$$', 'Expensive ($$$)'),
        ('$$$$', 'Luxury ($$$$)'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Location
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Contact
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # Details
    price_range = models.CharField(max_length=4, choices=PRICE_RANGE_CHOICES, default='$$')
    cuisine_type = models.ForeignKey(Cuisine, on_delete=models.SET_NULL, null=True, blank=True)

    # Ratings
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_reviews = models.IntegerField(default=0)

    # Delivery Options (optional feature – keep only if you use it in templates)
    has_uber_eats = models.BooleanField(default=False)
    has_doordash = models.BooleanField(default=False)
    has_grubhub = models.BooleanField(default=False)
    uber_eats_url = models.URLField(blank=True)
    doordash_url = models.URLField(blank=True)
    grubhub_url = models.URLField(blank=True)

    # External IDs
    google_place_id = models.CharField(max_length=200, blank=True, unique=True, null=True)

    # ✅ NEW: store SerpApi/Google Maps identifiers and photo URL
    # data_id lets you call get_place_details() / get_place_reviews()
    data_id = models.CharField(max_length=255, blank=True, default="")
    # thumbnail is a ready-to-render image URL from local_results
    thumbnail = models.URLField(max_length=500, blank=True, default="")

    yelp_id = models.CharField(max_length=200, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.city}"

    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"

    @property
    def delivery_options(self):
        """Return list of available delivery services"""
        options = []
        if self.has_uber_eats:
            options.append('Uber Eats')
        if self.has_doordash:
            options.append('DoorDash')
        if self.has_grubhub:
            options.append('Grubhub')
        return options

    class Meta:
        ordering = ['-rating', 'name']


class RestaurantDish(models.Model):
    """Junction table linking restaurants to dishes with pricing"""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='restaurant_dishes')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='dish_restaurants')

    # ✅ NEW: default price so you can populate relationships even without exact menu pricing
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Availability
    is_available = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.dish.name} at {self.restaurant.name} - ${self.price}"

    class Meta:
        unique_together = ['restaurant', 'dish']
        ordering = ['price']
        verbose_name = "Restaurant Dish"
        verbose_name_plural = "Restaurant Dishes"


class DishIngredient(models.Model):
    """Ingredients for dishes"""

    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    is_allergen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({'Allergen' if self.is_allergen else 'Ingredient'})"

    class Meta:
        ordering = ['name']
