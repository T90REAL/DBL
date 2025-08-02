import re
import json
import asyncio
import aiofiles

from app.agent.base import BaseAgent
from app.llm.base import BaseLLM


class ProblemParserAgent(BaseAgent):
    def __init__(self, name: str, description: str = None, llm: BaseLLM = None, port: int = 10045):
        super().__init__(
            name = name,
            description=description,
            llm=llm,
        )
        self.port = port
        self.host = "127.0.0.1"

    async def _write_to_file_async(self, filename: str, data: str):
        if data is None:
            return
        try:
            async with aiofiles.open(filename, "w", encoding="utf-8") as file:
                await file.write(data)
        except Exception as e:
            print(f"Error writing to file {filename}: {e}")

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, done_event: asyncio.Event,):
        """
        Processes a single client connection and sets an event upon successful processing.
        """
        addr = writer.get_extra_info("peername")
        print(f"Connected by {addr[0]}:{addr[1]}")

        try:
            headers = b""
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break
                headers += line

            headers_str = headers.decode("utf-8")
            match = re.search(r"Content-Length:\s*(\d+)", headers_str, re.IGNORECASE)

            if not match:
                print("Received a request without Content-Length. Ignoring.")
                return

            content_length = int(match.group(1))
            if content_length > 0:
                json_body = await reader.readexactly(content_length)
                json_data = json_body.decode("utf-8")
                print("Received JSON body successfully.")

                message = json.loads(json_data)
                tests = message.get("tests", [])
                write_tasks = []
                for i, test in enumerate(tests, start=1):
                    input_data = test.get("input")
                    output_data = test.get("output")
                    if input_data is not None:
                        write_tasks.append(
                            # Change the name of the input file
                            self._write_to_file_async(f"sol_{i}.in", input_data)
                        )
                    if output_data is not None:
                        write_tasks.append(
                            # Change the name of the answer file
                            self._write_to_file_async(f"ans_{i}.out", output_data)
                        )

                await asyncio.gather(*write_tasks)
                print(f"Data for {len(tests)} test cases has been written.")

                print("Task complete. Signaling server to shut down.")
                done_event.set()

        except Exception as e:
            print(f"An error occurred during connection handling: {e}")
        finally:
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            writer.write(response)
            await writer.drain()
            print(f"Closing connection from {addr[0]}:{addr[1]}")
            writer.close()
            await writer.wait_closed()

    async def listen_and_process_once(self):
        """
        Starts the server, processes one data reception, and then shuts down.
        """
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