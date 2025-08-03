import json
import aiofiles
from pathlib import Path

from app.protocols import AgentMessage
from app.agent.base import BaseLLM

async def analyze_problem(problem_dir: str, llm: BaseLLM) -> AgentMessage:
	"""
	Read the problem description and call LLM to extract the structured key information.
	"""
	source_name = "analyze_problem"
	print(f"\n[Tool: {source_name}]: Analyzing problem in '{problem_dir}'...")
	
	# handle the corner case
	if problem_dir.endswith("/"):
		problem_dir = problem_dir[:-1]

	problem_path = Path(problem_dir) / "problem.md"
	try:
		async with aiofiles.open(problem_path, "r", encoding="utf-8") as f:
			description = await f.read()
	except FileNotFoundError:
		error_msg = f"Could not find problem file at {problem_path}"
		print(f"[Tool: {source_name}]: {error_msg}")
		return AgentMessage(status="failure", source=source_name, message_type="error", error=error_msg)

	prompt = f"""
		You are a meticulous assistant for a competitive programming AI. Your task is to carefully read the following problem description and extract key information into a structured JSON format.

		### Problem Description
		{description}

		### Instructions
		Extract the following information and provide it in a single JSON object with the specified keys:
		1.  "problem_type": A brief classification of the problem (e.g., "Graph Theory", "Dynamic Programming", "Math", "String Manipulation", "Ad-hoc").
		2.  "input_format": A concise description of how the input is given from Standard Input.
		3.  "output_format": A concise description of what the program should print to Standard Output.
		4.  "constraints": A summary of all constraints on the input variables (e.g., "1 <= N <= 10^5", "All input values are integers.").

		Your response MUST be only the JSON object.
	"""
	
	messages = [
		{"role": "system", "content": "You are a meticulous assistant for a competitive programming AI. Your task is to carefully read the following problem description and extract key information into a structured JSON format."},
		{"role": "user", "content": prompt}
	]
	
	try:
		response_str, _ = await llm.chat(messages, format_type="json")

		analysis_data = json.loads(response_str)
		
		summary = "Successfully analyzed the problem and extracted key information."
		print(f"[Tool: {source_name}]: {summary}")
		return AgentMessage(
			source=source_name,
			message_type="tool_result",
			payload={"analysis": analysis_data}
		)
	except Exception as e:
		error_msg = f"Failed to analyze problem due to LLM or JSON parsing error: {e}"
		print(f"[Tool: {source_name}]: {error_msg}")
		return AgentMessage(
			status="failure",
			source=source_name,
			message_type="error",
			error=error_msg
		)


async def plan_solution_strategy(analysis: dict, description: str, llm: BaseLLM) -> AgentMessage:
	"""
	Based on the structured analysis results and original descriptions to develop a solution strategy.
	"""
	source_name = "plan_solution_strategy"
	print(f"\n[Tool: {source_name}]: Devising a solution strategy...")
	
	analysis_str = json.dumps(analysis, indent=2)

	prompt = f"""
		You are a world-class competitive programmer and algorithm expert. Your task is to devise a high-level plan to solve the given problem.

		### Structured Analysis of the Problem
		{analysis_str}

		### Full Problem Description
		{description}

		### Instructions
		Based on all the information provided, create a step-by-step plan to solve the problem. Your plan should include:
		1.  "algorithm": The name of the main algorithm or data structure to be used (e.g., "Dijkstra's Algorithm", "Segment Tree", "Depth First Search").
		2.  "data_structures": Any necessary data structures (e.g., "Adjacency List for graph", "Priority Queue", "2D DP array").
		3.  "step_by_step_plan": A concise, step-by-step natural language plan outlining the logic from reading input to printing the output.
		4.  "edge_cases_to_consider": A list of potential edge cases to be careful about (e.g., "Graph is disconnected", "N=1", "Constraints are at their maximum values").

		Respond with a single JSON object containing these keys. Your response MUST be only the JSON object.
	"""
	messages = [
		{"role": "system", "content": "You are a world-class competitive programmer and algorithm expert. Your task is to devise a high-level plan to solve the given problem."},
		{"role": "user", "content": prompt}
	]

	try:
		response_str, _ = await llm.chat(messages, format_type="json")
		plan_data = json.loads(response_str)
		
		summary = f"Successfully created a solution plan. Chosen algorithm: {plan_data.get('algorithm', 'N/A')}"
		print(f"[Tool: {source_name}]: {summary}")
		return AgentMessage(
			source=source_name,
			message_type="tool_result",
			payload={"plan": plan_data}
		)
	except Exception as e:
		error_msg = f"Failed to create a plan due to LLM or JSON parsing error: {e}"
		print(f"[Tool: {source_name}]: {error_msg}")
		return AgentMessage(status="failure", source=source_name, message_type="error", error=error_msg)
