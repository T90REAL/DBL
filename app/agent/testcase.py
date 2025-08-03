import json
import asyncio
import aiofiles
from pathlib import Path


from app.agent.base import BaseAgent


class TestCaseGeneratorAgent(BaseAgent):
	"""
	Reads a problem description and uses an LLM to generate additional test cases.
	"""
	async def _write_to_file_async(self, file_path: Path, data: str):
		if data is None:
			return
		try:
			file_path.parent.mkdir(parents=True, exist_ok=True)
			async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
				await file.write(data)
		except Exception as e:
			print(f"Error writing to file {file_path}: {e}")

		def _build_prompt(self, description: str, num_cases: int) -> str:
			"""Constructs a high-quality prompt for the LLM."""

			return f"""
				You are an expert test case creator for competitive programming. Your task is to generate {num_cases} diverse and challenging test cases for the following problem. Focus on edge cases based on the constraints.

				### Problem Description
				{description}

				### Instructions
				1.  Generate {num_cases} distinct test cases.
				2.  Cover edge cases: minimum values, maximum values, zero values, and any other special conditions mentioned.
				3.  Provide the output in a valid JSON format. The root object should be a single JSON object with one key "test_cases", which is an array of objects. Each object in the array must have two keys: "input" and "output".
				4.  Do not include the sample cases provided in the problem description. Create new ones.

				Example JSON format:
				{{
				"test_cases": [
					{{
						"input": "...",
						"output": "..."
					}},
					{{
						"input": "...",
						"output": "..."
					}}
				]
				}}
			"""
	
	async def execute(self, problem_md_path: Path, target_dir: Path, num_cases: int = 2):
		await self._log(f"Generating {num_cases} test cases for {problem_md_path.name}")

		try:
			async with aiofiles.open(problem_md_path, "r", encoding="utf-8") as f:
				description = await f.read()
		except FileNotFoundError:
			await self._log(f"Error: Could not find problem file at {problem_md_path}")
			return

		prompt = self._build_prompt(description, num_cases)
		messages = [{"role": "user", "content": prompt}]
		
		if not self.llm:
			await self._log("Error: LLM is not provided to the agent.")
			return
			
		llm_response_str, _ = await self.llm.chat(messages, format_type="json")

		try:
			response_data = json.loads(llm_response_str)
			generated_cases = response_data.get("test_cases", [])

			if not generated_cases or not isinstance(generated_cases, list):
				await self._log("Warning: LLM did not return a valid list of test cases.")
				return

			write_tasks = []
			# start in some large index
			start_index = 101 
			for i, case in enumerate(generated_cases, start=start_index):
				case_input = case.get("input")
				case_output = case.get("output")
				write_tasks.append(self._write_to_file_async(target_dir / f"sol_{i}.in", case_input))
				write_tasks.append(self._write_to_file_async(target_dir / f"ans_{i}.out", case_output))

			await asyncio.gather(*write_tasks)
			await self._log(f"Successfully generated and wrote {len(generated_cases)} new test cases to {target_dir}")

		except json.JSONDecodeError:
			await self._log(f"Error: Failed to decode JSON from LLM response. Response was: {llm_response_str}")
		except Exception as e:
			await self._log(f"An unexpected error occurred: {e}")
