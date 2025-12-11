from django.urls import path
from . import views

app_name = 'recommender'

urlpatterns = [
    # Main pages
    path('', views.recommender_home_view, name='recommender_home'),
    path('recommendations/', views.get_recommendations_view, name='get_recommendations'),
    path('similar/<int:dish_id>/', views.similar_dishes_view, name='similar_dishes'),

    # AI Features
    path('chat/', views.ai_chat_view, name='ai_chat'),
    path('api/chat/', views.ai_assistant_api, name='ai_assistant_api'),
    path('surprise/', views.surprise_me_view, name='surprise_me'),

    # Tools
    path('macro-calculator/', views.macro_calculator_view, name='macro_calculator'),
]