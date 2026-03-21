import os
import json
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — AI features will not work")
        self._client = genai.Client(api_key=api_key) if api_key else None

    def _generate(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("Gemini client not configured")
        response = self._client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text

    def parse_intent(self, user_text, history=None):
        try:
            history_text = ""
            if history:
                for msg in history:
                    role = "User" if msg['role'] == 'user' else "LinkUp Bot"
                    history_text += f"{role}: {msg['text']}\n"

            prompt = f"""
You are 'LinkUp', a helpful, friendly automated assistant for a Kasi Service App.
Your goal is to help users find services (plumbers, jobs, rooms).

CONVERSATION HISTORY:
{history_text}

CURRENT MESSAGE: "{user_text}"

TASK:
Return a JSON object.
1. If the user greets (hi, hello, sawubona), intent = 'greeting'.
2. If the user asks for a service (I need x, find me y), intent = 'search_listings'.
3. If the user is just chatting (Thank you, that's cool), intent = 'chat'.

JSON FORMAT:
{{
    "intent": "search_listings" OR "greeting" OR "chat",
    "category": "service/house/job",
    "keywords": "extracted keywords",
    "location": "extracted location",
    "chat_response": "If intent is 'chat', write a friendly short reply here."
}}
"""
            text = self._generate(prompt)
            clean = text.strip().replace("```json", "").replace("```", "")
            return json.loads(clean)

        except Exception as e:
            logger.error("AI intent parse error: %s", e)
            return {"intent": "unknown"}

    def generate_keywords(self, title, category):
        try:
            prompt = f"""
Generate 5 comma-separated search synonyms for a service.
Title: "{title}"
Category: "{category}"

Rules:
1. Return ONLY the words separated by commas.
2. No intro text, no markdown.
"""
            return self._generate(prompt).lower().strip()
        except Exception as e:
            logger.warning("AI keyword generation failed: %s", e)
            return title.lower()


ai_brain = AIService()
