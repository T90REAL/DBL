import ollama

from app.llm.base import BaseLLM

class LAN_LLM(BaseLLM):
    """
    This is a class for user to select the desired LLM and run it on your own Lan-server.
    """

    def __init__(self, model_name: str, host: str):
        """
        Initialize the LLM using Ollama based on the name of the model and the ip of the local server.

        Args:
            host (str): Ollama server ip address, such as "http://192.168.1.100:10000".
                - you can test your service by using `curl ip_address` to check if Ollama is running or not.
        """

        self.host = host
        print(f"Start connecting to the host: {host}...")
        super().__init__(model_name=model_name)

    def _create_client(self):
        return ollama.AsyncClient(host=self.host)