from app.agent.parser import *


async def main():
    contest_url = "https://atcoder.jp/contests/abc363"

    agent = GetProblemAgent(name="work")
    await agent.execute(contest_url=contest_url)

if __name__ == "__main__":
    asyncio.run(main())