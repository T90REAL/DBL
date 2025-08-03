from app.llm.base import BaseLLM

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple, Optional


class BaseAgent(BaseModel, ABC):
    """Base class for all agents."""
    name: str = Field(..., description="The unique name of the tool")
    description: Optional[str] = Field(default=None, description="Clear and brief description of the agent")
    llm: Optional[BaseLLM] = Field(None, description="The selected large language model (brain).")
    memory: list = Field([], description="The memory of the agent.")

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """
         Args:
            context (Dict[str, Any]): A dictionary that contains contextual information about the current problem and is passed between agents.
            return (Dict[str, Any]): Updated context.
        """
        pass

    async def _log(self, message: str):
        """Asynchronous logging that shows which agent is doing what."""
        print(f"[{self.name}]: {message}")

    def clear(self):
        self.memory.clear()