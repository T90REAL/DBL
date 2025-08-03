import json
import asyncio
from typing import List
from pathlib import Path

from app.tool.parser import *
from app.protocols import AgentMessage


async def parser_pipeline(contest_url: str) -> AgentMessage:
    """
    A deterministic pipeline that is responsible for the complete parsing of all question information for a contest.
    It calls multiple parsing tool functions sequentially.

    Returns:
        A JSON string summarizing the result, including the paths to problem directories.
    """
    print(f"\n--- Running Parsing Pipeline for: {contest_url} ---")
    
    source_name = "parser_pipeline"
    contest_urls_msg = await parse_contest_page(contest_url)

    if contest_urls_msg.status == 'failure':
        print("--- Pipeline Finished with CRITICAL a FAILURE ---")
        return contest_urls_msg
    
    problem_urls = contest_urls_msg.payload.get("problem_urls", [])

    if not problem_urls:
        summary = "Pipeline finished: No problem URLs were found."
        print(f"--- {summary} ---")
        return AgentMessage(
            source=source_name, 
            message_type="pipeline_result", 
            payload={"summary": summary, "problem_directories": []}
        )

    contest_name = contest_url.strip("/").split("/")[-1]
    base_dir = Path(contest_name)
    base_dir.mkdir(exist_ok=True)

    parsing_tasks = []
    problem_dirs = []
    for url in problem_urls:
        problem_id = url.strip("/").split("/")[-1]
        target_dir = base_dir / problem_id
        problem_dirs.append(str(target_dir))
        task = parse_problem_page(problem_url=url, target_dir=target_dir)
        parsing_tasks.append(task)

    results = await asyncio.gather(*parsing_tasks)

    failed_tasks = [res for res in results if res.status == 'failure']
    if failed_tasks:
        print(f"Warning: {len(failed_tasks)} sub-tasks failed during parsing.")

    summary = f"Parsing pipeline completed. Processed {len(problem_urls)} problems into '{base_dir}'."
    print(f"--- Pipeline Finished: {summary} ---")

    return AgentMessage(
        source=source_name,
        message_type="pipeline_result",
        payload={
            "summary": summary,
            "problem_directories": problem_dirs,
            "sub_task_results": [res.model_dump() for res in results]
        }
    )