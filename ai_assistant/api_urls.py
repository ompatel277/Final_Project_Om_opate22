from django.urls import path
from . import api_views

app_name = 'ai_assistant_api'

urlpatterns = [
    path('chat/', api_views.ChatView.as_view(), name='chat'),
    path('ingredient/<str:ingredient>/', api_views.IngredientInfoView.as_view(), name='ingredient-info'),
    path('substitution/', api_views.SubstitutionView.as_view(), name='substitution'),
    path('recommend/', api_views.RecommendationView.as_view(), name='recommend'),
    path('feedback/', api_views.FeedbackView.as_view(), name='feedback'),
    path('history/', api_views.QueryHistoryView.as_view(), name='history'),
]
