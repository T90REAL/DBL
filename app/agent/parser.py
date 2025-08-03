import re
import httpx
import asyncio
import aiofiles
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from app.agent.base import BaseAgent


class ContestParserAgent(BaseAgent):
    """
    Visit the contest homepage and parse out the URLs of all problems.
    """
    async def execute(self, contest_url: str) -> list[str]:
        await self._log(f"Parsing the contest page: {contest_url}")
        problem_urls = []
        try:
            tasks_url = contest_url.rstrip('/') + '/tasks'
            
            async with httpx.AsyncClient() as client:
                await self._log(f"Request problem list page: {tasks_url}")
                response = await client.get(tasks_url, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            
            task_rows = soup.select("div.table-responsive table tbody tr")
            
            if not task_rows:
                await self._log("Warning: using selectors 'div.table-responsive table tbody tr' No subject lines were found.")
                return []

            for row in task_rows:
                link_element = row.find("a")
                if link_element and 'href' in link_element.attrs:
                    problem_path = link_element['href']
                    full_url = urljoin(tasks_url, problem_path)
                    if full_url not in problem_urls:
                        problem_urls.append(full_url)
            
            if problem_urls:
                await self._log(f"Parsed successfully, found {len(problem_urls)} problems.")
            else:
                await self._log("WARNING: Although the title form was found, it failed to parse out any links.")

            return problem_urls

        except httpx.HTTPStatusError as e:
            await self._log(f"HTTP error when requesting a page: {e.response.status_code} {e.response.reason_phrase} for url {e.request.url}")
            return []
        except Exception as e:
            await self._log(f"Error parsing contest page: {e}")
            return []


class ProblemParserAgent(BaseAgent):
    """
    Receives a problem URL, actively crawls and parses all the statement, and stores it in the corresponding folder.
    """
    async def _write_to_file_async(self, file_path: Path, data: str):
        if data is None:
            return
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
                await file.write(data)
        except Exception as e:
            print(f"Error occurs when writing into file {file_path}: {e}")

    async def execute(self, problem_url: str, target_dir: Path):
        await self._log(f"Start processing problem: {problem_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(problem_url, follow_redirects=True, timeout=15)
                response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            await self._log(f"Failed to access page: {e}")
            return

        description_text = "Description not found."
        title = "Title not found"
        # limits_text = "Limits not found"
        
        if "atcoder.jp" in problem_url:
            title_element = soup.find("h2") or soup.find("span", class_="h2")
            if title_element: title = title_element.text.strip()

            desc_element = soup.find("span", class_="lang-en") or soup.find("div", id="task-statement")
            if desc_element: description_text = desc_element.get_text(separator=" ", strip=True)

            # limits_p = desc_element.find("p") if desc_element else None
            # if limits_p: limits_text = limits_p.get_text(separator=" ", strip=True)

        # sample parsing
        samples = []
        if "atcoder.jp" in problem_url:
            sample_headers = soup.find_all("h3", string=re.compile(r"Sample Input\s*\d+"))
            for i, header in enumerate(sample_headers, 1):
                input_pre = header.find_next_sibling("pre")
                output_header = soup.find("h3", string=f"Sample Output {i}")
                output_pre = output_header.find_next_sibling("pre") if output_header else None
                
                if input_pre and output_pre:
                    samples.append({
                        "input": input_pre.get_text(),
                        "output": output_pre.get_text()
                    })

        # Preparing to write
        write_tasks = []
        
        # Write statement
        description_content = f"# {title}\n\n**URL:** {problem_url}\n\n---\n\n{description_text}"
        write_tasks.append(self._write_to_file_async(target_dir / "problem.md", description_content))
        
        # write_tasks.append(self._write_to_file_async(target_dir / "limits.txt", limits_text))
        
        # Write sample
        for i, sample in enumerate(samples, 1):
            write_tasks.append(self._write_to_file_async(target_dir / f"sol_{i}.in", sample["input"]))
            write_tasks.append(self._write_to_file_async(target_dir / f"ans_{i}.out", sample["output"]))
            
        await asyncio.gather(*write_tasks)
        await self._log(f"Successfully fetch the problem into the folder: {target_dir}")

class GetProblemAgent(BaseAgent):
    """
    Dispatch 'ContestParserAgent' and 'ProblemParserAgent' to get the problems information of a specific contest.
    """

    async def execute(self, contest_url: str):
        contest_parser = ContestParserAgent(name="ContestParser")
        problem_parser = ProblemParserAgent(name="ProblemParser")

        # Obtaining links of all problems
        problem_urls = await contest_parser.execute(contest_url)
        
        if not problem_urls:
            print("Failed to get any topic links and the program exited.")
            return

        contest_name = contest_url.strip("/").split("/")[-1]
        base_dir = Path(contest_name)
        base_dir.mkdir(exist_ok=True)
        
        print(f"\Start processing {len(problem_urls)} problems, storing into '{contest_name}' folders...")

        parsing_tasks = []
        for url in problem_urls:
            problem_id = url.strip("/").split("/")[-1]
            target_dir = base_dir / problem_id
            task = problem_parser.execute(problem_url=url, target_dir=target_dir)
            parsing_tasks.append(task)
            
        await asyncio.gather(*parsing_tasks)
        
        print(f"\nAll problems are properly processed!")