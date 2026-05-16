import os
import openai
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self, model_name: str = None):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")

        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model_name or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    async def generate(self, prompt: str, system_message: str = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # Run synchronous call in executor to avoid blocking
        loop = __import__('asyncio').get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
        )
        return response.choices[0].message.content