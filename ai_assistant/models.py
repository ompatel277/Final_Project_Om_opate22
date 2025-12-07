from django.db import models
from django.contrib.auth.models import User


class AIQueryLog(models.Model):
    """Log AI assistant interactions"""

    QUERY_TYPE_CHOICES = [
        ('ingredient', 'Ingredient Information'),
        ('nutrition', 'Nutrition Facts'),
        ('substitution', 'Substitution Suggestion'),
        ('recommendation', 'Dish Recommendation'),
        ('general', 'General Question'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_queries')

    # Query details
    query_type = models.CharField(max_length=20, choices=QUERY_TYPE_CHOICES, default='general')
    user_message = models.TextField()
    ai_response = models.TextField()

    # Context
    related_dish_id = models.IntegerField(null=True, blank=True)
    conversation_id = models.CharField(max_length=100, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    # Feedback
    was_helpful = models.BooleanField(null=True, blank=True)
    feedback_text = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.query_type} at {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "AI Query Log"
        verbose_name_plural = "AI Query Logs"


class ConversationContext(models.Model):
    """Store conversation context for multi-turn conversations"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation_id = models.CharField(max_length=100, unique=True)

    # Context data (stored as JSON)
    context_data = models.JSONField(default=dict)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.conversation_id}"

    class Meta:
        ordering = ['-updated_at']
