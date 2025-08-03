import asyncio
import json
from pathlib import Path

from app.tool.pipeline import *
from app.agent.base import BaseAgent
from app.protocols import AgentMessage
from app.agent.solver import ProblemSolverAgent
from app.tool.registry import ToolRegistry, Tool
from app.prompt.OVERALL_GOAL import OVERALL_GOAL_PROMPT

class MasterAgent(BaseAgent):
    """
    Chief Commander of the Competition. Responsible for planning and distributing tasks to subordinate ProblemSolverAgents.
    """
    async def execute(self, initial_goal: str, contest_url: str):
        await self._log(f"--- MasterAgent Activated. Goal: {initial_goal} ---")

        # 1. 执行固定的解析流水线
        # 在一个更复杂的系统中，MasterAgent的LLM可以在这里决策是否需要解析，
        # 但根据您的要求，我们先将其作为固定第一步。
        await self._log("Executing deterministic parsing pipeline as the first step.")
        parsing_result_msg = await parser_pipeline(contest_url)

        if parsing_result_msg.status == 'failure':
            await self._log(f"CRITICAL FAILURE: Parsing pipeline failed. Reason: {parsing_result_msg.error}")
            return

        await self._log("Parsing pipeline completed successfully.")
        
        # distribute a solver for each prob
        problem_dirs_str = parsing_result_msg.payload.get("problem_directories", [])
        problem_dirs = [Path(p) for p in problem_dirs_str]

        if not problem_dirs:
            await self._log("No problems found to solve. Shutting down.")
            return

        # prepare tools for each solver 
        solver_tool_registry = self._create_solver_tool_registry()
        
        solver_tasks = []
        for p_dir in problem_dirs:
            solver_agent = ProblemSolverAgent(
                problem_dir=p_dir,
                tool_registry=solver_tool_registry,
                llm=self.llm # TODO: use a fine-tuned llm for CP
            )
            
            solver_tasks.append(
                solver_agent.execute(overall_goal=OVERALL_GOAL_PROMPT)
            )
        
        # execute
        await self._log(f"Dispatching {len(solver_tasks)} ProblemSolverAgents to work in parallel...")
        solver_results = await asyncio.gather(*solver_tasks)
        
        await self._log("\n--- All ProblemSolverAgents have finished. Final Report: ---")
        successful_solves = 0
        for res in solver_results:
            if res.status == 'success':
                successful_solves += 1
            print(res.to_json())
        
        await self._log(f"\nContest processing complete. {successful_solves}/{len(solver_results)} problems were successfully processed.")

    def _create_solver_tool_registry(self) -> ToolRegistry:
        """定义 ProblemSolverAgent 能使用的工具。"""
        # from app.tool.creative_tools import generate_test_cases # 假设
        # from app.tool.coding_tools import generate_code # 假设

        # 这是一个模拟的工具函数存根
        async def generate_test_cases(problem_dir: str, num_cases: int = 3) -> AgentMessage:
            print(f"[Tool: generate_test_cases]: Generating {num_cases} cases for '{problem_dir}'...")
            await asyncio.sleep(1) # 模拟工作
            return AgentMessage(
                source="generate_test_cases",
                message_type="tool_result",
                payload={"summary": f"Generated {num_cases} cases."}
            )

        registry = ToolRegistry()
        registry.register_function(
            func=generate_test_cases,
            name="generate_additional_test_cases",
            description="Generates extra edge-case tests for the current problem. Parameters: {'num_cases': 'int'}"
        )
        # registry.register_function(func=generate_code, ...)
        return registry