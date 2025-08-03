SOLVE_PROB_PROMPT = """
You are an expert problem-solving agent. Your goal is: "{goal}" for the problem located in the directory '{self.problem_dir}'.

### Problem Statement (first 1500 chars)
{problem_statement[:1500]}... 

### History of actions for THIS problem:
---
{history_str}
---

{tools_prompt}

Based on the problem statement and history, what is the next single tool to use to solve this problem?
Your response MUST be a single JSON object with "tool_name" and "parameters".
If you believe the problem is solved or no further action is needed, use the "finish" tool.
"""