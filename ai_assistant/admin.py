from django.contrib import admin
from .models import AIQueryLog, ConversationContext


@admin.register(AIQueryLog)
class AIQueryLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'query_type', 'created_at', 'response_time_ms', 'was_helpful']
    list_filter = ['query_type', 'was_helpful', 'created_at']
    search_fields = ['user__username', 'user_message', 'ai_response']
    readonly_fields = ['created_at', 'response_time_ms']

    fieldsets = (
        ('User & Type', {
            'fields': ('user', 'query_type', 'conversation_id')
        }),
        ('Query Details', {
            'fields': ('user_message', 'ai_response', 'related_dish_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'response_time_ms')
        }),
        ('Feedback', {
            'fields': ('was_helpful', 'feedback_text')
        }),
    )


@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    list_display = ['user', 'conversation_id', 'last_message_at', 'created_at']
    search_fields = ['user__username', 'conversation_id']
    readonly_fields = ['created_at', 'updated_at']
