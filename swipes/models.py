from django.db import models
from django.contrib.auth.models import User
from dishes.models import Dish, Restaurant


class SwipeAction(models.Model):
    """Track user swipes on dishes"""

    SWIPE_CHOICES = [
        ('right', 'Right (Like)'),
        ('left', 'Left (Pass)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swipes')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='swipes')
    direction = models.CharField(max_length=10, choices=SWIPE_CHOICES)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} swiped {self.direction} on {self.dish.name}"

    class Meta:
        unique_together = ['user', 'dish']
        ordering = ['-created_at']
        verbose_name = "Swipe Action"
        verbose_name_plural = "Swipe Actions"


class Favorite(models.Model):
    """User's favorite dishes"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_dishes')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='favorited_by')

    # Optional notes
    notes = models.TextField(blank=True, help_text="Personal notes about this dish")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ♥ {self.dish.name}"

    class Meta:
        unique_together = ['user', 'dish']
        ordering = ['-created_at']
        verbose_name = "Favorite Dish"
        verbose_name_plural = "Favorite Dishes"


class FavoriteRestaurant(models.Model):
    """User's favorite restaurants"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_restaurants')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='favorited_by')

    # Optional notes
    notes = models.TextField(blank=True, help_text="Personal notes about this restaurant")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ♥ {self.restaurant.name}"

    class Meta:
        unique_together = ['user', 'restaurant']
        ordering = ['-created_at']
        verbose_name = "Favorite Restaurant"
        verbose_name_plural = "Favorite Restaurants"


class Blacklist(models.Model):
    """Dishes or ingredients user wants to avoid"""

    BLACKLIST_TYPE_CHOICES = [
        ('dish', 'Dish'),
        ('ingredient', 'Ingredient'),
        ('cuisine', 'Cuisine'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklist')

    # What is blacklisted
    blacklist_type = models.CharField(max_length=20, choices=BLACKLIST_TYPE_CHOICES)
    item_name = models.CharField(max_length=200, help_text="Name of dish, ingredient, or cuisine to avoid")

    # Optional reason
    reason = models.TextField(blank=True, help_text="Why you're avoiding this")

    # Reference to actual dish if applicable
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, null=True, blank=True, related_name='blacklisted_by')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} blacklisted {self.item_name} ({self.blacklist_type})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Blacklist Item"
        verbose_name_plural = "Blacklist Items"


class SwipeSession(models.Model):
    """Track swipe sessions for analytics"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swipe_sessions')

    # Session stats
    total_swipes = models.IntegerField(default=0)
    right_swipes = models.IntegerField(default=0)
    left_swipes = models.IntegerField(default=0)

    # Session timing
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Filters used
    cuisine_filter = models.CharField(max_length=100, blank=True)
    meal_type_filter = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username}'s session on {self.started_at.date()}"

    @property
    def match_rate(self):
        """Calculate percentage of right swipes"""
        if self.total_swipes == 0:
            return 0
        return round((self.right_swipes / self.total_swipes) * 100, 1)

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Swipe Session"
        verbose_name_plural = "Swipe Sessions"