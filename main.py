from app.agent.get_prob import *
from app.llm.lan import LAN_LLM
from app.llm.ollama import Ollama_LLM
from app.tool.pipeline import *


async def main():
    contest_url = "https://atcoder.jp/contests/abc363"
    await parser_pipeline(contest_url=contest_url)

    # agent = GetProblemAgent(name="work")
    # await agent.execute(contest_url=contest_url)

if __name__ == "__main__":
    asyncio.run(main())