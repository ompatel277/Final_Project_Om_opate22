from django.contrib import admin
from .models import (
    Review, ReviewHelpful, WeeklyRanking, TrendingDish,
    CommunityChallenge, ChallengeParticipation, UserBadge
)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'dish', 'rating', 'title', 'helpful_count', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['user__username', 'dish__name', 'title', 'content']
    readonly_fields = ['helpful_count', 'created_at', 'updated_at']
    list_editable = ['is_verified']

    fieldsets = (
        ('Review Info', {
            'fields': ('user', 'dish', 'rating', 'title', 'content', 'image')
        }),
        ('Meta', {
            'fields': ('helpful_count', 'is_verified', 'created_at', 'updated_at')
        }),
    )


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['user', 'review', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'review__title']


@admin.register(WeeklyRanking)
class WeeklyRankingAdmin(admin.ModelAdmin):
    list_display = ['rank', 'dish', 'week_start', 'week_end', 'total_swipes', 'right_swipes', 'match_rate',
                    'average_rating']
    list_filter = ['week_start', 'week_end']
    search_fields = ['dish__name']
    readonly_fields = ['created_at']
    ordering = ['week_start', 'rank']


@admin.register(TrendingDish)
class TrendingDishAdmin(admin.ModelAdmin):
    list_display = ['current_rank', 'dish', 'trending_score', 'recent_swipes_24h', 'recent_swipes_7d', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['dish__name']
    readonly_fields = ['last_updated']
    ordering = ['current_rank']

    actions = ['recalculate_trending_score']

    def recalculate_trending_score(self, request, queryset):
        for trending in queryset:
            trending.calculate_trending_score()
        self.message_user(request, f"Recalculated trending scores for {queryset.count()} dishes.")

    recalculate_trending_score.short_description = "Recalculate trending scores"


@admin.register(CommunityChallenge)
class CommunityChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'start_date', 'end_date', 'challenge_type']
    list_filter = ['status', 'challenge_type', 'start_date']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    filter_horizontal = ['participants']

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'challenge_type', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Challenge Details', {
            'fields': ('target_dish', 'target_cuisine', 'reward_description', 'image')
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChallengeParticipation)
class ChallengeParticipationAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'completed', 'progress_count', 'joined_at']
    list_filter = ['completed', 'joined_at']
    search_fields = ['user__username', 'challenge__title']
    readonly_fields = ['joined_at', 'completed_at']


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'icon', 'name', 'badge_type', 'earned_at']
    list_filter = ['badge_type', 'earned_at']
    search_fields = ['user__username', 'name']
    readonly_fields = ['earned_at']