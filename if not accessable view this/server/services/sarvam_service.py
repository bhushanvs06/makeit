import os
import openai
from dotenv import load_dotenv

load_dotenv()

class SarvamService:
    def __init__(self, model_name: str = None):
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY environment variable not set")

        # Sarvam requires the key in the api-subscription-key header.
        # We'll build a custom HTTP client that injects this header.
        import httpx
        http_client = httpx.Client(
            base_url="https://api.sarvam.ai/v1",
            headers={"api-subscription-key": api_key},
        )
        self.client = openai.OpenAI(
            api_key=api_key,          # still required by the SDK
            base_url="https://api.sarvam.ai/v1",
            http_client=http_client,
        )
        self.model = model_name or os.getenv("SARVAM_MODEL", "sarvam-30b")

    async def generate(self, prompt: str, system_message: str = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # Run the synchronous API call in a thread pool
        loop = __import__('asyncio').get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            ),
        )
        return response.choices[0].message.content