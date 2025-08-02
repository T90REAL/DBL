import re
import sys
import ollama

from app.llm.base import BaseLLM

class Ollama_LLM(BaseLLM):
    """
    This is a class for user to select the desired LLM and run it on your PC based on Ollama platform.
    More model details can be found in: https://ollama.com.
    """

    def __init__(self, model_name: str):
        super().__init__(model_name=model_name)
    
    def _create_client(self):
        return ollama.AsyncClient()