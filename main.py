import asyncio

from app.agent.parser import ProblemParserAgent
from app.agent.parser import ProblemParserAgent


async def main():
    receiver = ProblemParserAgent(name="parser")
    await receiver.execute()


if __name__ == "__main__":
    asyncio.run(main())