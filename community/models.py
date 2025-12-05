from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from dishes.models import Dish, Restaurant
from django.utils import timezone
from datetime import timedelta


class Review(models.Model):
    """User reviews for dishes"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='reviews')

    # Rating
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )

    # Review content
    title = models.CharField(max_length=200)
    content = models.TextField()

    # Optional image
    image = models.ImageField(upload_to='reviews/', null=True, blank=True)

    # Helpful votes
    helpful_count = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False, help_text="Verified purchase/order")

    def __str__(self):
        return f"{self.user.username}'s review of {self.dish.name} - {self.rating}★"

    class Meta:
        unique_together = ['user', 'dish']
        ordering = ['-created_at']
        verbose_name = "Review"
        verbose_name_plural = "Reviews"


class ReviewHelpful(models.Model):
    """Track which users found reviews helpful"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} found review #{self.review.id} helpful"

    class Meta:
        unique_together = ['user', 'review']


class WeeklyRanking(models.Model):
    """Weekly top dishes ranking"""

    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='weekly_rankings')

    # Week identification
    week_start = models.DateField()
    week_end = models.DateField()

    # Ranking position
    rank = models.IntegerField()

    # Stats for the week
    total_swipes = models.IntegerField(default=0)
    right_swipes = models.IntegerField(default=0)
    reviews_count = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Week {self.week_start} - #{self.rank}: {self.dish.name}"

    @property
    def match_rate(self):
        """Calculate percentage of right swipes"""
        if self.total_swipes == 0:
            return 0
        return round((self.right_swipes / self.total_swipes) * 100, 1)

    class Meta:
        ordering = ['week_start', 'rank']
        unique_together = ['dish', 'week_start']
        verbose_name = "Weekly Ranking"
        verbose_name_plural = "Weekly Rankings"


class TrendingDish(models.Model):
    """Track trending dishes with time-decay algorithm"""

    dish = models.OneToOneField(Dish, on_delete=models.CASCADE, related_name='trending')

    # Trending score (calculated)
    trending_score = models.FloatField(default=0.0)

    # Contributing factors
    recent_swipes_24h = models.IntegerField(default=0)
    recent_swipes_7d = models.IntegerField(default=0)
    recent_reviews_7d = models.IntegerField(default=0)

    # Ranking
    current_rank = models.IntegerField(null=True, blank=True)

    # Metadata
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trending #{self.current_rank}: {self.dish.name}" if self.current_rank else f"Trending: {self.dish.name}"

    def calculate_trending_score(self):
        """Calculate trending score with time decay"""
        now = timezone.now()

        # Base score from recent activity
        score = 0

        # Recent swipes (24h) - highest weight
        score += self.recent_swipes_24h * 10

        # Recent swipes (7d) - medium weight
        score += self.recent_swipes_7d * 2

        # Recent reviews - high weight
        score += self.recent_reviews_7d * 15

        # Dish rating - bonus multiplier
        if self.dish.average_rating > 4.0:
            score *= 1.5
        elif self.dish.average_rating > 3.5:
            score *= 1.2

        self.trending_score = score
        self.save()

        return score

    class Meta:
        ordering = ['-trending_score']
        verbose_name = "Trending Dish"
        verbose_name_plural = "Trending Dishes"


class CommunityChallenge(models.Model):
    """Community challenges and events"""

    CHALLENGE_STATUS = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()

    # Challenge type
    challenge_type = models.CharField(max_length=50, default='weekly')

    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=CHALLENGE_STATUS, default='upcoming')

    # Challenge details
    target_dish = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True, blank=True)
    target_cuisine = models.CharField(max_length=100, blank=True)

    # Participation
    participants = models.ManyToManyField(User, through='ChallengeParticipation', related_name='challenges')

    # Prize/Reward
    reward_description = models.CharField(max_length=200, blank=True)

    # Image
    image = models.ImageField(upload_to='challenges/', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Community Challenge"
        verbose_name_plural = "Community Challenges"


class ChallengeParticipation(models.Model):
    """Track user participation in challenges"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(CommunityChallenge, on_delete=models.CASCADE)

    # Progress
    completed = models.BooleanField(default=False)
    progress_count = models.IntegerField(default=0)

    # Dates
    joined_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}"

    class Meta:
        unique_together = ['user', 'challenge']


class UserBadge(models.Model):
    """Achievements and badges for users"""

    BADGE_TYPE = [
        ('swiper', 'Swiper'),
        ('reviewer', 'Reviewer'),
        ('explorer', 'Explorer'),
        ('foodie', 'Foodie'),
        ('social', 'Social'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')

    # Badge info
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, default="🏆")

    # Metadata
    earned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name} {self.icon}"

    class Meta:
        ordering = ['-earned_at']
        verbose_name = "User Badge"
        verbose_name_plural = "User Badges"