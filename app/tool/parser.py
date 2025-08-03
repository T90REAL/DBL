import re
import httpx
import asyncio
import aiofiles
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any

from app.protocols import AgentMessage


async def _write_to_file_async(file_path: Path, data: str):
    """Write data to a file asynchronously."""
    if data is None:
        return
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
            await file.write(data)
    except Exception as e:
        print(f"Error occurs when writing into file {file_path}: {e}")


async def parse_contest_page(contest_url: str) -> AgentMessage:
    """
    Tool function: accesses the contest homepage and parses out the URLs of all the problems for that contest.
    
    Args:
        contest_url (str): URL of the contest.

    Returns:
        List[str]: Absolute URL of problems.
    """
    print(f"[Tool: parse_contest_page]: Parsing the contest page: {contest_url}")
    source_name = "parse_contest_page"
    problem_urls = []
    try:
        tasks_url = contest_url.rstrip('/') + '/tasks'
        
        async with httpx.AsyncClient() as client:
            print(f"[Tool: parse_contest_page]: Requesting problem list page: {tasks_url}")
            response = await client.get(tasks_url, follow_redirects=True)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        task_rows = soup.select("div.table-responsive table tbody tr")
        
        if not task_rows:
            print("[Tool: parse_contest_page]: Warning: No subject lines were found.")
        else:
            for row in task_rows:
                link_element = row.find("a")
                if link_element and 'href' in link_element.attrs:
                    problem_path = link_element['href']
                    full_url = urljoin(tasks_url, problem_path)
                    if full_url not in problem_urls:
                        problem_urls.append(full_url)
            
        print(f"[Tool: parse_contest_page]: Parsed successfully, found {len(problem_urls)} problems.")

        return AgentMessage(
            source=source_name,
            message_type="tool_result",
            payload={"problem_urls": problem_urls}
        )

    except Exception as e:
        error_msg = f"Error parsing contest page: {e}"
        print(f"[Tool: parse_contest_page]: {error_msg}")
        return AgentMessage(
            status="failure",
            source=source_name,
            message_type="error",
            error=error_msg
        )

async def parse_problem_page(problem_url: str, target_dir: Path) -> AgentMessage:
    """
    Tool function: receives a problem URL, grabs and parses all the information and stores it in the specified folder.

    Args:
        problem_url (str): URL of a single problem.
        target_dir (Path): Path to the destination folder where the parsing results will be stored.
        
    Returns:
        str: A summary string describing the results of the execution.
    """
    print(f"[Tool: parse_problem_page]: Start processing problem: {problem_url}")
    source_name = "parse_problem_page"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(problem_url, follow_redirects=True, timeout=15)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        error_msg = f"Failed to access page: {e}"
        print(f"[Tool: parse_problem_page]: {error_msg}")
        return AgentMessage(
            status="failure", 
            source=source_name, 
            message_type="error", 
            error=error_msg)

    description_text = "Description not found."
    title = "Title not found"
    
    if "atcoder.jp" in problem_url:
        title_element = soup.find("h2") or soup.find("span", class_="h2")
        if title_element: 
            # fix: remove the 'Editorial' from title
            editorial_link = title_element.find("a")
            if editorial_link:
                editorial_link.decompose()
            
            title = title_element.text.strip()

        desc_element = soup.find("span", class_="lang-en") or soup.find("div", id="task-statement")
        if desc_element: description_text = desc_element.get_text(separator=" ", strip=True)

    samples = []
    if "atcoder.jp" in problem_url:
        sample_headers = soup.find_all("h3", string=re.compile(r"Sample Input\s*\d+"))
        for i, header in enumerate(sample_headers, 1):
            input_pre = header.find_next_sibling("pre")
            output_header = soup.find("h3", string=f"Sample Output {i}")
            output_pre = output_header.find_next_sibling("pre") if output_header else None
            if input_pre and output_pre:
                samples.append({"input": input_pre.get_text(), "output": output_pre.get_text()})

    write_tasks = []
    description_content = f"# {title}\n\n**URL:** {problem_url}\n\n---\n\n{description_text}"
    write_tasks.append(_write_to_file_async(target_dir / "problem.md", description_content))
    for i, sample in enumerate(samples, 1):
        write_tasks.append(_write_to_file_async(target_dir / f"sol_{i}.in", sample["input"]))
        write_tasks.append(_write_to_file_async(target_dir / f"ans_{i}.out", sample["output"]))
        
    await asyncio.gather(*write_tasks)
    
    summary = f"Successfully fetched the problem '{title}' into the folder: {target_dir}"
    print(f"[Tool: parse_problem_page]: {summary}")
    
    return AgentMessage(
        source=source_name,
        message_type="tool_result",
        payload={"summary": summary, "target_dir": str(target_dir)}
    )