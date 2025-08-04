import os
import sys
import openai
from typing import Optional

from app.agent.base import BaseLLM

class ApiLLM(BaseLLM):
    """
    A pure API LLM implementation for connecting to cloud services that require API keys (e.g. OpenAI, Groq, etc.).
    It uses the openai library as a generic interface.
    NOTE: Using ApiLLM.create(...) to create LLM is safer.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Args:
            model_name (str): name of the model to use (e.g., "gpt-4o", "llama3-8b-8192").
            api_key (Optional[str]): API key. If None, will try to read it from the environment variable.
            base_url (Optional[str]): address of the API. If None, the official OpenAI address is used.
        """
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("API Key not found. Please pass it as an argument or set an environment variable (e.g., OPENAI_API_KEY, GROQ_API_KEY).")
        
        self.base_url = base_url
        super().__init__(model_name)

    def _create_client(self):
        return openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _check_model_exists(self):
        try:
            print(f"Verifying if model '{self.model_name}' is available at '{self.base_url or 'OpenAI official API'}'...")
            models_response = await self.client.models.list()
            available_models = [m.id for m in models_response.data]
            
            if self.model_name not in available_models:
                raise ValueError(f"Model '{self.model_name}' not found in the list of available models.")

            print(f"Model '{self.model_name}' is available.")

        except Exception as e:
            print(f"Could not verify model with the API. Please check your API key and model name. Error: {e}")
            sys.exit(1)

    async def chat(self, messages: list, format_type: Optional[str] = None) -> tuple:
        try:
            chat_options = {
                "model": self.model_name,
                "messages": messages,
                "n": 1,
            }
            if format_type == "json":
                print(f"  (Using JSON mode for '{self.model_name}')")
                chat_options["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**chat_options)

            content = response.choices[0].message.content

            return content, "NOT AVAILABLE"

        except Exception as e:
            error_message = f"An error occurred while interacting with the API: {e}"
            print(error_message)
            return error_message, None