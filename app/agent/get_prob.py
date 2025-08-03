from pathlib import Path
import asyncio

from app.agent.base import BaseAgent
from app.tool.parser import parse_contest_page, parse_problem_page


class GetProblemAgent(BaseAgent):
    """
    As a pipeline orchestrator, it dispatches tool functions to get problem information.
    """
    async def execute(self, contest_url: str):
        # get the tool
        problem_urls = await parse_contest_page(contest_url)
        
        if not problem_urls:
            print("Failed to get any problem links and the program exited.")
            return

        contest_name = contest_url.strip("/").split("/")[-1]
        base_dir = Path(contest_name)
        base_dir.mkdir(exist_ok=True)
        
        print(f"\nStart processing {len(problem_urls)} problems, storing into '{contest_name}' folders...")

        parsing_tasks = []
        for url in problem_urls:
            problem_id = url.strip("/").split("/")[-1]
            target_dir = base_dir / problem_id
            task = parse_problem_page(problem_url=url, target_dir=target_dir)
            parsing_tasks.append(task)
            
        await asyncio.gather(*parsing_tasks)
        
        print(f"\nAll problems are properly processed!")
        