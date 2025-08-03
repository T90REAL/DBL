import asyncio
import json
from pathlib import Path

from app.protocols import AgentMessage
from app.tool.pipeline import parser_pipeline
from app.tool.think import analyze_problem, plan_solution_strategy
from app.llm.ollama import OllamaLLM
from app.llm.lan import LANLLM
from app.tool.case_gen import decide_and_generate_test_cases

async def main():
    contest_url = "https://atcoder.jp/contests/abc363"
    print("--- STAGE 1: Preparing problem data... ---")
    parsing_result_msg = await parser_pipeline(contest_url)
    if parsing_result_msg.status == 'failure':
        print(f"Pipeline failed: {parsing_result_msg.error}")
        return
    problem_dirs_str = parsing_result_msg.payload.get("problem_directories", [])
    if not problem_dirs_str:
        print("No problem directories found.")
        return
    
    target_problem_dir = Path(problem_dirs_str[2])
    print(f"\n--- SETUP COMPLETE. Target for testing: {target_problem_dir} ---")

    # llm = OllamaLLM(model_name="gemma3:4b")
    llm = OllamaLLM(model_name="deepseek-r1:8b")

    print("\n--- STAGE 2: Executing 'analyze_problem' tool... ---")
    
    analysis_msg = await analyze_problem(problem_dir=str(target_problem_dir), llm=llm)
    
    print("\n--- ANALYSIS RESULT ---")
    print(analysis_msg.to_json())
    
    if analysis_msg.status == 'failure':
        print("\nAnalysis failed. Stopping test.")
        return

    try:
        description = (target_problem_dir / "problem.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        print("Could not read problem description for planning step.")
        return
        
    print("\n--- STAGE 3: Executing 'plan_solution_strategy' tool... ---")
    plan_msg = await plan_solution_strategy(
        analysis=analysis_msg.payload.get("analysis", {}),
        description=description,
        llm=llm
    )
    
    print("\n--- PLAN RESULT ---")
    print(plan_msg.to_json())

    print("\n--- STAGE 4: Executing 'decide_and_generate_test_cases' tool... ---")
    generation_decision_msg = await decide_and_generate_test_cases(
        plan=plan_msg.payload.get("plan", {}),
        description=description,
        problem_dir=str(target_problem_dir),
        llm=llm
    )
    
    print("\n--- FINAL RESULT OF THE FLOW ---")
    print(generation_decision_msg.to_json())
    
    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())