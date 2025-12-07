from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import AIQueryLog, ConversationContext
from .serializers import (
    ChatMessageSerializer, ChatResponseSerializer,
    AIQueryLogSerializer, FeedbackSerializer
)
from .services import ai_service
from dishes.models import Dish
import json


class ChatView(APIView):
    """Main chat endpoint for AI assistant"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id') or ai_service.generate_conversation_id()
        dish_id = serializer.validated_data.get('dish_id')
        query_type = serializer.validated_data.get('query_type', 'general')

        # Get or create conversation context
        context_obj, _ = ConversationContext.objects.get_or_create(
            user=user,
            conversation_id=conversation_id
        )

        # Build context
        context = {}

        # Add dish context if provided
        if dish_id:
            try:
                dish = Dish.objects.get(id=dish_id)
                context['dish'] = {
                    'name': dish.name,
                    'description': dish.description,
                    'calories': dish.calories,
                    'is_vegetarian': dish.is_vegetarian,
                    'is_vegan': dish.is_vegan,
                }
            except Dish.DoesNotExist:
                pass

        # Add user preferences
        profile = user.profile
        context['user_preferences'] = {
            'diet_type': profile.diet_type,
            'allergies': profile.allergies,
            'favorite_cuisines': profile.favorite_cuisines,
        }

        # Get conversation history
        conversation_history = context_obj.context_data.get('messages', [])

        # Generate response
        ai_response, response_time = ai_service.generate_response(
            message,
            conversation_history=conversation_history,
            context=context
        )

        # Update conversation context
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": ai_response})

        # Keep only last 10 messages
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        context_obj.context_data['messages'] = conversation_history
        context_obj.save()

        # Log query
        query_log = AIQueryLog.objects.create(
            user=user,
            query_type=query_type,
            user_message=message,
            ai_response=ai_response,
            related_dish_id=dish_id,
            conversation_id=conversation_id,
            response_time_ms=response_time
        )

        # Generate suggestions (optional)
        suggestions = self._generate_suggestions(query_type)

        response_data = {
            'response': ai_response,
            'conversation_id': conversation_id,
            'query_log_id': query_log.id,
            'suggestions': suggestions
        }

        return Response(ChatResponseSerializer(response_data).data)

    def _generate_suggestions(self, query_type):
        """Generate follow-up suggestions"""
        suggestions_map = {
            'ingredient': [
                "Tell me about common allergens",
                "What are good substitutes?",
                "Nutritional benefits?"
            ],
            'nutrition': [
                "How can I make this healthier?",
                "What are the macros?",
                "Any dietary concerns?"
            ],
            'substitution': [
                "Other alternatives?",
                "Which substitute is healthiest?",
                "Vegan options?"
            ],
            'recommendation': [
                "Tell me more about the first dish",
                "Any other cuisines?",
                "Lower calorie options?"
            ],
            'general': [
                "Recommend me a dish",
                "What are your capabilities?",
                "Help me find something healthy"
            ]
        }

        return suggestions_map.get(query_type, [])


class IngredientInfoView(APIView):
    """Get information about a specific ingredient"""
    permission_classes = [IsAuthenticated]

    def get(self, request, ingredient):
        response = ai_service.get_ingredient_info(ingredient)

        # Log query
        AIQueryLog.objects.create(
            user=request.user,
            query_type='ingredient',
            user_message=f"Information about {ingredient}",
            ai_response=response
        )

        return Response({'ingredient': ingredient, 'info': response})


class SubstitutionView(APIView):
    """Get substitution suggestions"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ingredient = request.data.get('ingredient')
        dietary_restriction = request.data.get('dietary_restriction')

        if not ingredient:
            return Response(
                {"error": "ingredient is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        response = ai_service.get_substitution(ingredient, dietary_restriction)

        # Log query
        AIQueryLog.objects.create(
            user=request.user,
            query_type='substitution',
            user_message=f"Substitutes for {ingredient}",
            ai_response=response
        )

        return Response({
            'ingredient': ingredient,
            'dietary_restriction': dietary_restriction,
            'substitutions': response
        })


class RecommendationView(APIView):
    """Get dish recommendations"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        preferences = {
            'diet_type': profile.diet_type,
            'allergies': profile.allergies,
            'favorite_cuisines': profile.favorite_cuisines,
            'calorie_goal': profile.daily_calorie_goal,
        }

        response = ai_service.recommend_dishes(preferences)

        # Log query
        AIQueryLog.objects.create(
            user=request.user,
            query_type='recommendation',
            user_message="Recommend dishes based on my preferences",
            ai_response=response
        )

        return Response({'recommendations': response})


class FeedbackView(APIView):
    """Submit feedback on AI responses"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_log_id = serializer.validated_data['query_log_id']
        was_helpful = serializer.validated_data['was_helpful']
        feedback_text = serializer.validated_data.get('feedback_text', '')

        query_log = get_object_or_404(
            AIQueryLog,
            id=query_log_id,
            user=request.user
        )

        query_log.was_helpful = was_helpful
        query_log.feedback_text = feedback_text
        query_log.save()

        return Response({"status": "feedback_saved"})


class QueryHistoryView(APIView):
    """Get user's query history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 20))

        queries = AIQueryLog.objects.filter(
            user=request.user
        ).order_by('-created_at')[:limit]

        serializer = AIQueryLogSerializer(queries, many=True)
        return Response(serializer.data)
