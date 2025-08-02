import asyncio

from app.agent.parser import ProblemParserAgent
from app.agent.parser import ProblemParserAgent


async def main():
    receiver = ProblemParserAgent()
    await receiver.listen_and_process_once()


if __name__ == "__main__":
    asyncio.run(main())