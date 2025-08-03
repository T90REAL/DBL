from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


class AgentMessage(BaseModel):
    """
    Standard message format for communication between Agent and Tool.
    """
    status: Literal["success", "failure", "in_progress"] = "success"
    
    # from which agent / tool
    source: str = Field(..., description="The name of the agent or tool that sent the message.")
    
    # purpose of the message
    message_type: str = Field(..., description="The type of the message (e.g., 'tool_result', 'final_summary').")
    
    # main data, can be any type
    payload: Any = Field(None, description="The main data payload of the message.")
    
    # fail details
    error: Optional[str] = Field(None, description="Error details if the status is 'failure'.")

    def to_json(self) -> str:
        """Serialize messages to JSON strings for history."""
        return self.model_dump_json(indent=2)