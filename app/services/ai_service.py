import json
import google.generativeai as genai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure the Gemini client only if the key is provided
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class AIService:
    @staticmethod
    def _get_model():
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        # We use a standard generative model (e.g., gemini-1.5-pro or gemini-1.5-flash)
        return genai.GenerativeModel(settings.GEMINI_MODEL)

    @staticmethod
    async def categorize_ticket(title: str, description: str) -> dict:
        """
        Analyzes a ticket's title and description to automatically categorize it and
        assign an initial priority. Returns a JSON-compatible dictionary.
        """
        prompt = f"""
        You are an expert customer support AI. Analyze the following support ticket and classify it.
        Return ONLY a raw JSON dictionary (no markdown, no backticks) with exactly two keys: 'category' and 'priority'.
        
        The 'category' should be a short string (e.g., "Billing", "Technical Support", "Bug Report", "Feature Request", "General").
        The 'priority' must be exactly one of: "Low", "Medium", "High", "Urgent".

        Ticket Title: {title}
        Ticket Description: {description}
        """

        try:
            model = AIService._get_model()
            # Run asynchronously
            response = await model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean up markdown formatting if the model still includes it
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.endswith("```"):
                text = text[:-3]
                
            result = json.loads(text.strip())
            
            # Basic validation
            valid_priorities = ["Low", "Medium", "High", "Urgent"]
            if result.get("priority") not in valid_priorities:
                result["priority"] = "Medium"
                
            return {
                "category": result.get("category", "General"),
                "priority": result.get("priority", "Medium")
            }
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            # Graceful degradation if AI fails
            return {"category": "General", "priority": "Medium"}

    @staticmethod
    async def suggest_reply(history: str) -> str:
        """
        Takes a string representation of a ticket's history and generates a professional response draft.
        """
        prompt = f"""
        You are an expert customer support agent. 
        Read the following conversation history for a support ticket and generate a polite, professional, and helpful reply to the customer.
        Do not include internal notes in your reasoning, just provide the raw message that should be sent to the customer.
        Keep it concise but empathetic.

        Conversation History:
        {history}

        Draft Response:
        """

        try:
            model = AIService._get_model()
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI reply suggestion failed: {e}")
            return "I apologize, but I am currently unable to generate a response. Please review the ticket manually."
