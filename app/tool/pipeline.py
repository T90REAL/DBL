import json
import asyncio
from typing import List
from pathlib import Path

from app.tool.parser import *


async def parser_pipeline(contest_url: str) -> str:
    """
    A deterministic pipeline that is responsible for the complete parsing of all question information for a contest.
    It calls multiple parsing tool functions sequentially.

    Returns:
        A JSON string summarizing the result, including the paths to problem directories.
    """
    print(f"\n--- Running Parsing Pipeline for: {contest_url} ---")

    problem_urls = await parse_contest_page(contest_url)

    if not problem_urls:
        result = {
            "status": "failure",
            "message": f"Pipeline failed: Could not retrieve any problem URLs from {contest_url}.",
        }
        return json.dumps(result)

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

    await asyncio.gather(*parsing_tasks)

    summary = f"Parsing pipeline completed. Processed {len(problem_urls)} problems into '{base_dir}'."
    print(f"--- Pipeline Finished: {summary} ---")

    result = {
        "status": "success",
        "message": summary,
        "problem_directories": problem_dirs,
    }
    return json.dumps(result)
