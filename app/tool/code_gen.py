import json
import re
from pathlib import Path

from app.protocols import AgentMessage
from app.agent.base import BaseLLM
from app.tool.parser import _write_to_file_async


async def generate_code(plan: dict, description: str, problem_dir: str, llm: BaseLLM) -> AgentMessage:
    """
    Generate source code for the solution based on the solution plan and topic description.
    """
    source_name = "generate_code"
    print(f"\n[Tool: {source_name}]: Generating code for problem in '{problem_dir}'...")
    
    plan_str = json.dumps(plan, indent=2)

    prompt = f"""
        You are a world-class competitive programmer, an expert in writing clean, efficient, and correct Python code.

        Your task is to write a complete and correct Python solution without comments for the following problem.

        ### Full Problem Description
        {description}

        ### Your Detailed Plan
        {plan_str}

        ### Instructions
        1.  Write a complete Python program that solves the problem.
        2.  Read all input from standard input (stdin).
        3.  Write all output to standard output (stdout).
        4.  Make sure it pass all the samples.
        5.  Your response MUST contain ONLY the raw Python code. Do not include any extra text, explanations, or comments in the code.
        6.  Enclose the code in a ```python ... ``` markdown block.
    """
    messages = [
        {"role": "system", "content": "You are a world-class competitive programmer, an expert in writing clean, efficient, and correct Python code without comments."},
        {"role": "user", "content": prompt}
    ]

    try:
        response_str, _ = await llm.chat(messages)
        
        # use 're' to get code part
        match = re.search(r"```python\s*\n(.*?)\n\s*```", response_str, re.DOTALL)
        if not match:
            # TODO: the output is not in the specific format, may cause some error
            code = response_str
            print("Warning: generating might have some error. This is the code that llm gives : \n{code}")
        else:
            code = match.group(1)

        if not code.strip():
            return AgentMessage(status="failure", source=source_name, message_type="error", error="LLM returned empty code.")

        target_path = Path(problem_dir)
        code_file_path = target_path / "main.py"
        await _write_to_file_async(code_file_path, code)
        
        summary = f"Successfully generated Python code and saved to '{code_file_path}'."
        print(f"[Tool: {source_name}]: {summary}")
        return AgentMessage(
            source=source_name,
            message_type="tool_result",
            payload={"summary": summary, "code_path": str(code_file_path)}
        )
    except Exception as e:
        error_msg = f"Failed to generate code due to an error: {e}"
        print(f"[Tool: {source_name}]: {error_msg}")
        return AgentMessage(status="failure", source=source_name, message_type="error", error=error_msg)