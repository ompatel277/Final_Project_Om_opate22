import openai
from django.conf import settings
from typing import Dict, List, Optional
import time
import uuid


class AIAssistantService:
    """Service for AI assistant functionality using OpenAI"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key

        self.system_prompt = """You are a helpful food assistant for Swipe&Bite, 
        a food discovery app. You help users with:
        - Ingredient information and allergen details
        - Nutrition facts and dietary information
        - Substitution suggestions for ingredients
        - Dish recommendations based on preferences
        - General food-related questions

        Be friendly, concise, and accurate. If you're unsure about something, 
        say so rather than making up information."""

    def generate_response(
            self,
            user_message: str,
            conversation_history: Optional[List[Dict]] = None,
            context: Optional[Dict] = None
    ) -> tuple[str, int]:
        """Generate AI response using OpenAI"""

        start_time = time.time()

        if not self.api_key:
            return (
                "AI Assistant is not configured. Please add your OpenAI API key to use this feature.",
                0
            )

        try:
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add context if provided
            if context:
                context_message = self._build_context_message(context)
                messages.append({"role": "system", "content": context_message})

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            ai_response = response.choices[0].message.content
            response_time = int((time.time() - start_time) * 1000)

            return ai_response, response_time

        except Exception as e:
            error_response = f"I'm sorry, I encountered an error: {str(e)}"
            response_time = int((time.time() - start_time) * 1000)
            return error_response, response_time

    def _build_context_message(self, context: Dict) -> str:
        """Build context message from provided context"""

        parts = []

        if 'dish' in context:
            dish = context['dish']
            parts.append(f"Current dish: {dish['name']}")
            if 'description' in dish:
                parts.append(f"Description: {dish['description']}")
            if 'calories' in dish:
                parts.append(f"Calories: {dish['calories']}")

        if 'user_preferences' in context:
            prefs = context['user_preferences']
            if 'diet_type' in prefs and prefs['diet_type'] != 'none':
                parts.append(f"User diet: {prefs['diet_type']}")
            if 'allergies' in prefs and prefs['allergies']:
                parts.append(f"User allergies: {prefs['allergies']}")

        return " | ".join(parts) if parts else ""

    def get_ingredient_info(self, ingredient: str) -> str:
        """Get information about an ingredient"""

        prompt = f"""Provide concise information about the ingredient '{ingredient}':
        1. What is it?
        2. Common allergens (if any)
        3. Nutritional highlights
        Keep it brief (3-4 sentences)."""

        response, _ = self.generate_response(prompt)
        return response

    def get_substitution(self, ingredient: str, dietary_restriction: Optional[str] = None) -> str:
        """Get substitution suggestions for an ingredient"""

        restriction_text = f" (for {dietary_restriction} diet)" if dietary_restriction else ""
        prompt = f"""Suggest 3 good substitutes for '{ingredient}'{restriction_text}.
        For each substitute, briefly explain why it works."""

        response, _ = self.generate_response(prompt)
        return response

    def recommend_dishes(self, preferences: Dict) -> str:
        """Recommend dishes based on user preferences"""

        context = {"user_preferences": preferences}
        prompt = "Based on my dietary preferences, suggest 5 dishes I might enjoy and explain why."

        response, _ = self.generate_response(prompt, context=context)
        return response

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID"""
        return str(uuid.uuid4())


# Singleton instance
ai_service = AIAssistantService()
