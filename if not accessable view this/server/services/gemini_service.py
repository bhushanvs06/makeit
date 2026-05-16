import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions as google_exceptions

load_dotenv()

class GeminiService:
    def __init__(self, model_name: str = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        # Allow model override via env var
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    @retry(
        retry=retry_if_exception_type(google_exceptions.ResourceExhausted),
        wait=wait_exponential(multiplier=1, min=5, max=60),
        stop=stop_after_attempt(3)
    )
    async def generate(self, prompt: str, system_message: str = None) -> str:
        full_prompt = prompt if not system_message else f"{system_message}\n\n{prompt}"
        try:
            response = await self.model.generate_content_async(full_prompt)
            return response.text
        except google_exceptions.ResourceExhausted as e:
            # The retry decorator will handle this, but we re-raise so tenacity sees it
            raise
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")