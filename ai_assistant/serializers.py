from rest_framework import serializers
from .models import AIQueryLog, ConversationContext


class AIQueryLogSerializer(serializers.ModelSerializer):
    """Serializer for AIQueryLog"""

    class Meta:
        model = AIQueryLog
        fields = [
            'id', 'query_type', 'user_message', 'ai_response',
            'related_dish_id', 'conversation_id', 'created_at',
            'response_time_ms', 'was_helpful', 'feedback_text'
        ]
        read_only_fields = ['created_at']


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for chat messages"""

    message = serializers.CharField(required=True)
    conversation_id = serializers.CharField(required=False, allow_blank=True)
    dish_id = serializers.IntegerField(required=False, allow_null=True)
    query_type = serializers.ChoiceField(
        choices=AIQueryLog.QUERY_TYPE_CHOICES,
        default='general'
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses"""

    response = serializers.CharField()
    conversation_id = serializers.CharField()
    query_log_id = serializers.IntegerField()
    suggestions = serializers.ListField(child=serializers.CharField(), required=False)


class FeedbackSerializer(serializers.Serializer):
    """Serializer for feedback"""

    query_log_id = serializers.IntegerField(required=True)
    was_helpful = serializers.BooleanField(required=True)
    feedback_text = serializers.CharField(required=False, allow_blank=True)
