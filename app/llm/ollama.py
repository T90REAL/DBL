import re
import sys
import ollama

from app.llm.base import BaseLLM

class OllamaLLM(BaseLLM):
    """
    This is a class for user to select the desired LLM and run it on your PC based on Ollama platform.
    More model details can be found in: https://ollama.com.
    NOTE: Using OllamaLLM.create(...) to create LLM is safer.
    """

    def __init__(self, model_name: str):
        """
        Initialize the LLM using Ollama based on the name of the model and the ip of the local server.

        Args:
            model_name (str): The model that is going to be used, such as "deepseek-r1:14b", "qwen3:8b"
            More model details can be found in:
                - https://ollama.com
                - https://huggingface.co/models
        """
        super().__init__(model_name=model_name)
    
    def _create_client(self):
        return ollama.AsyncClient(host='http://localhost:11434')