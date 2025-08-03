import asyncio
import json
import aiofiles
from pathlib import Path

from app.protocols import AgentMessage
from app.agent.base import BaseLLM
from app.tool.parser import _write_to_file_async


async def decide_and_generate_test_cases(plan: dict, description: str, problem_dir: str, llm: BaseLLM) -> AgentMessage:
    """
    1. the LLM is first to decide whether additional test cases need to be generated for the problem.
    2. if they are needed, generate them based on the edge_cases in the plan stage.
    """
    source_name = "decide_and_generate_test_cases"
    print(f"\n[Tool: {source_name}]: Evaluating plan for problem in '{problem_dir}'...")

    decision_prompt = f"""
        You are a strategic assistant. Your task is to decide if generating additional test cases is a valuable and feasible action for the given problem, based on its plan.
        If the implementation is too complicated or impossible, you should decide to not to generate.
        
        ### Problem Solving Plan
        {json.dumps(plan, indent=2)}

        ### Key Considerations
        - **High Value**: Generation is valuable for problems with tricky edge cases (e.g., graph connectivity, number theory properties, max/min constraints).
        - **Low Value/Infeasible**: Generation is not useful for interactive problems, output-only problems, or problems where the output is not uniquely determined by the input (e.g., creative constructions).

        ### Your Decision
        Based on the plan, especially the 'algorithm' and 'edge_cases_to_consider', is it a good idea to generate more test cases?
        Respond with a single JSON object: {{"should_generate": boolean, "reason": "your brief reasoning"}}.
        Your response MUST be only the JSON object.
    """
    
    try:
        decision_response_str, _ = await llm.chat(
            [
                {"role": "system", "content": "You are a strategic assistant. Your task is to decide if generating additional test cases is a valuable and feasible action for the given problem, based on its plan. If the implementation is too complicated or impossible, you should decide to not to generate."},
                {"role": "user", "content": decision_prompt}
            ], format_type="json")
        decision = json.loads(decision_response_str)
        
        should_generate = decision.get("should_generate", False)
        reason = decision.get("reason", "No reason provided.")
        print(f"[Tool: {source_name}]: Decision: Should generate? {should_generate}. Reason: {reason}")

        if not should_generate:
            return AgentMessage(
                source=source_name,
                message_type="tool_result",
                payload={"summary": f"Skipped test case generation. Reason: {reason}"}
            )
    except Exception as e:
        error_msg = f"Failed during decision step: {e}"
        print(f"[Tool: {source_name}]: {error_msg}")
        return AgentMessage(status="failure", source=source_name, message_type="error", error=error_msg)

    print(f"[Tool: {source_name}]: Proceeding with test case generation...")
    
    generation_prompt = f"""
        You are an expert test case creator in competitive programming. Based on the provided problem description and a list of edge cases to consider, generate several new, challenging test cases.

        ### Full Problem Description
        {description}

        ### Edge Cases to Focus On
        {plan.get('edge_cases_to_consider', 'No specific edge cases listed.')}

        ### Instructions
        - Create several distinct test cases that specifically target the edge cases mentioned above.
        - Provide the output in a valid JSON format: {{"test_cases": [{{"input": "...", "output": "..."}}]}}.
        - Do not repeat the official sample cases.
        - Your response MUST be only the JSON object.
    """
    try:
        generation_response_str, _ = await llm.chat(
        [
            {"role": "system", "content": "You are an expert test case creator in competitive programming. Based on the provided problem description and a list of edge cases to consider, generate several new, challenging test cases."},
            {"role": "user", "content": generation_prompt}
        ], format_type="json")
        generated_data = json.loads(generation_response_str)
        test_cases = generated_data.get("test_cases", [])

        if not test_cases:
            return AgentMessage(
                status="failure",
                source=source_name,
                message_type="error",
                error="LLM failed to generate any test cases."
            )

        target_path = Path(problem_dir)
        write_tasks = []
        start_index = 101 # start from a relatively large index
        for i, case in enumerate(test_cases, start=start_index):
            case_input = case.get("input", "")
            case_output = case.get("output", "")
            
            write_tasks.append(_write_to_file_async(target_path / f"sol_{i}.in", case_input))
            write_tasks.append(_write_to_file_async(target_path / f"ans_{i}.out", case_output))
        
        await asyncio.gather(*write_tasks)

        summary = f"Successfully decided to generate and created {len(test_cases)} new test cases in '{problem_dir}'."
        print(f"[Tool: {source_name}]: {summary}")
        return AgentMessage(
            source=source_name,
            message_type="tool_result",
            payload={"summary": summary, "generated_count": len(test_cases)}
        )

    except Exception as e:
        error_msg = f"Failed during generation step: {e}"
        print(f"[Tool: {source_name}]: {error_msg}")
        return AgentMessage(status="failure", source=source_name, message_type="error", error=error_msg)