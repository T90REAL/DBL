import json
from pathlib import Path

from app.agent.base import BaseAgent
from app.tool.registry import ToolRegistry
from app.protocols import AgentMessage

MAX_STEP = 5

class ProblemSolverAgent(BaseAgent):
    """
    An agent responsible for solving individual problems. 
    It has its own “think-act” loop and calls on specific problem solving tools.
    """
    def __init__(self, problem_dir: Path, tool_registry: ToolRegistry, **kwargs):
        super().__init__(name=f"Solver-{problem_dir.name}", **kwargs)
        self.problem_dir = problem_dir
        self.tool_registry = tool_registry

    def _build_prompt(self, goal: str) -> str:
        history_str = "\n".join(self.memory) if self.memory else "This is the first step. Analyze the problem and decide what to do next."
        tools_prompt = self.tool_registry.get_tools_prompt()
        
        try:
            problem_statement = (self.problem_dir / "problem.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            problem_statement = "Error: problem.md not found."

        return f"""
            You are an expert competitive programming problem-solving agent. Your goal is: "{goal}" for the problem located in the directory '{self.problem_dir}'.

            ### Problem Statement
            {problem_statement}

            ### History of your actions for THIS problem:
            ---
            {history_str}
            ---

            Here are the tools that you might use:
            {tools_prompt}

            Based on the problem statement and history, what is the next single tool to use to solve this problem?
            Your response MUST be a single JSON object with "tool_name" and "parameters".
            If you believe the problem is solved or no further action is needed, use the "finish" tool.
        """

    async def execute(self, overall_goal: str) -> AgentMessage:
        """Perform a single prob solution process."""
        await self._log(f"Activating to solve problem. Goal: {overall_goal}")

        for i in range(MAX_STEP): # avoid infinite loop
            await self._log(f"--- Step {i+1}: Thinking about problem '{self.problem_dir.name}' ---")
            
            prompt = self._build_prompt(overall_goal)
            # TODO: change the chat
            response_str, _ = await self.llm.chat([{"role": "user", "content": prompt}], format_type="json")
            
            try:
                action = json.loads(response_str)
                tool_name = action.get("tool_name")
                parameters = action.get("parameters", {})
            except Exception as e:
                self.memory.append(f"Result: Failed to parse LLM response. Error: {e}")
                continue

            self.memory.append(f"Step {i+1}: Decided to use tool '{tool_name}' with parameters: {parameters}")
            
            # terminate the task successfully
            if tool_name == "finish":
                summary = f"Problem in '{self.problem_dir.name}' considered complete. Reason: {parameters.get('reason')}"
                await self._log(summary)
                return AgentMessage(source=self.name, message_type="final_summary", payload={"summary": summary})

            tool_obj = self.tool_registry.get_tool(tool_name)
            if not tool_obj:
                self.memory.append(f"Result: Error, tool '{tool_name}' does not exist.")
                continue

            try:
                if "problem_dir" in tool_obj.callable.__code__.co_varnames:
                    parameters["problem_dir"] = str(self.problem_dir)
                
                result_msg: AgentMessage = await tool_obj.callable(**parameters)
                self.memory.append(f"Result from {tool_name}: {result_msg.model_dump_json(indent=2)}")
            except Exception as e:
                self.memory.append(f"Result: Error executing tool '{tool_name}': {e}")
        
        final_summary = f"Reached max steps for problem '{self.problem_dir.name}'. See history for details."
        return AgentMessage(
            source=self.name, 
            status="failure", 
            message_type="max_steps_reached", 
            payload={"summary": final_summary, "history": self.memory}
        )