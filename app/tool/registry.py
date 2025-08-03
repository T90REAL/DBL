from typing import Dict, Optional, Any, Callable, Coroutine
from dataclasses import dataclass, field

from app.prompt.GET_TOOL import GET_TOOL_PROMPT

@dataclass
class Tool:
    """A generic tool definition."""
    name: str
    description: str
    callable: Callable[..., Coroutine[Any, Any, Any]]

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_function(self, func: Callable, name: str, description: str):
        tool = Tool(name=name, description=description, callable=func)
        self._tools[tool.name] = tool
        print(f"[ToolRegistry]: Tool '{tool.name}' registered.")
        
    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_tools_prompt(self) -> str:
        """Provide tools' description to llm."""
        if not self._tools: return "No tools available."
        
        prompt = GET_TOOL_PROMPT
        for name, tool in self._tools.items():
            prompt += f"### Tool: {name}\n- Description: {tool.description}\n\n"
        return prompt