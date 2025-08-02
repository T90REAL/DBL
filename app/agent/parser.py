import re
import json
import httpx
import asyncio
import aiofiles
from bs4 import BeautifulSoup


from app.agent.base import BaseAgent
from app.llm.base import BaseLLM


class ProblemParserAgent(BaseAgent):
    port: int = 10045
    host: str = "127.0.0.1"

    async def _write_to_file_async(self, filename: str, data: str):
        if data is None:
            return
        try:
            async with aiofiles.open(filename, "w", encoding="utf-8") as file:
                await file.write(data)
        except Exception as e:
            print(f"Error writing to file {filename}: {e}")
            
    async def _fetch_and_parse_description(self, url: str) -> str:
        """
        Asynchronously fetch the web page HTML and parse out the title description.
        """
        await self._log(f"Fetching from {url} to get problem data...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=15)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            
            # different selector based on platform
            description_element = None
            if "atcoder.jp" in url:
                description_element = soup.find("span", class_="lang-en") or soup.find("div", id="task-statement")
            elif "codeforces.com" in url:
                # TODO: Not work anymore
                description_element = soup.find("div", class_="problem-statement")
            
            if description_element:
                await self._log("Successfully get the problem info.")
                return description_element.get_text(separator=" ", strip=True)
            else:
                await self._log("WARNING: Failure to find a platform-specific title description element will return an empty description.")
                return "Could not automatically parse problem description from the webpage."

        except Exception as e:
            await self._log(f"Error in obtaining or parsing the statement: {e}")
            return f"Error fetching description: {e}"

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, done_event: asyncio.Event,):
        addr = writer.get_extra_info("peername")
        print(f"Connected by {addr[0]}:{addr[1]}")
        try:
            headers_str = ""
            while True:
                line = await reader.readline()
                if not line or line == b'\r\n': break
                headers_str += line.decode('utf-8')

            match = re.search(r"Content-Length:\s*(\d+)", headers_str, re.IGNORECASE)
            if not match: return

            content_length = int(match.group(1))
            if content_length > 0:
                json_body = await reader.readexactly(content_length)
                message = json.loads(json_body.decode("utf-8"))
                
                problem_url = message.get("url", "")
                if not problem_url:
                    print("Error: URL not received from competitive-companion.")
                    return
                
                fetch_desc_task = self._fetch_and_parse_description(problem_url)

                problem_title = message.get("name", "N/A")
                time_limit_ms = message.get("timeLimit", 1000)
                memory_limit_mb = message.get("memoryLimit", 256)
                limits_content = f"Time Limit: {time_limit_ms} ms\nMemory Limit: {memory_limit_mb} MB\n"
                
                full_description = await fetch_desc_task
                
                write_tasks = []
                description_content = f"# {problem_title}\n\n**URL:** {problem_url}\n\n---\n\n{full_description}"
                write_tasks.append(self._write_to_file_async("problem.md", description_content))
                write_tasks.append(self._write_to_file_async("limits.txt", limits_content))

                tests = message.get("tests", [])
                for i, test in enumerate(tests, start=1):
                    write_tasks.append(self._write_to_file_async(f"sol_{i}.in", test.get("input")))
                    write_tasks.append(self._write_to_file_async(f"ans_{i}.out", test.get("output")))

                await asyncio.gather(*write_tasks)
                print(f"All info have been written to files.")
                done_event.set()

        except Exception as e:
            print(f"An error occurred while processing the connection: {e}")
        finally:
            response = (b"HTTP/1.1 200 OK\r\n" b"Access-Control-Allow-Origin: *\r\n" b"Connection: close\r\n" b"\r\n")
            writer.write(response)
            await writer.drain()
            print(f"Closing connection from {addr[0]}:{addr[1]}")
            writer.close()
            await writer.wait_closed()

    async def execute(self):
        done_event = asyncio.Event()
        handler = lambda r, w: self._handle_connection(r, w, done_event)
        server = await asyncio.start_server(handler, self.host, self.port)
        print(f"Listening on {self.host}:{self.port}... Waiting for a single data payload.")
        try:
            await done_event.wait()
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
        finally:
            print("Shutting down server.")
            if server.is_serving():
                server.close()
                await server.wait_closed()
            print("Server stopped.")
