import re
import sys
import asyncio
from typing import Optional
from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """An abstract LLM class."""

    def __init__(self, model_name: str):
        """
        Initialize the LLM based on the name of the model

        Args:
            model_name (str): The model that is going to be used, such as "deepseek-r1:14b", "qwen3:8b"
            More model details can be found in:
                - https://ollama.com
                - https://huggingface.co/models
        """

        print(f"Start initializing the LLM: {model_name}...")
        self.model_name = model_name
        self.client = self._create_client()

    @classmethod
    async def create(cls, model_name: str, **kwargs):
        instance = cls(model_name=model_name, **kwargs)

        await instance._check_model_exists()

        return instance

    @abstractmethod
    def _create_client(self):
        """
        An abstract method need to be implemented by different type of LLM.
        """
        pass

    async def _check_model_exists(self):
        """Check if the model is available on different platform."""
        try:
            response = await self.client.list()
            server_models = [model["model"] for model in response["models"]]

            if self.model_name not in server_models:
                # TODO: Ask user to download manully or hiddenly
                raise ValueError(
                    f"Your input model '{self.model_name}' is not on the server's list."
                )
            else:
                print(f"Found the model '{self.model_name}' on the server!")

        except Exception as e:
            print(f"Can not build the service. Error : {e}")
            sys.exit(1)

    async def chat(self, messages: list, format_type: Optional[str] = None) -> tuple:
        """This method could communicate with the LLM. Return the Tuple(response part, response time)."""
        try:
            chat_options = {
                "model": self.model_name,
                "messages": messages,
                # "options": {"temperature": 0}
            }

            # TODO: some model does not contain the 'format_type' option, such as 'gemma'
            # add a whitelist and use re?
            # the deepseek reasoning model can support this option
            if format_type == "json":
                chat_options["format"] = "json"

            response = await self.client.chat(**chat_options)
            content = response["message"]["content"]
            response_time = response["created_at"]

            return content, response_time

        except Exception as e:
            error_message = f"Some error occur when interacting: {e}"
            print(error_message)
            return error_message
