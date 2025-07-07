import asyncio
import os

from dotenv import load_dotenv

from aidial_bing_grounding.agent.cache import create_project
from aidial_bing_grounding.ai_project.api import get_agents_by_name

load_dotenv(override=True)


async def main():
    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]

    print(f"Connection string: {project_endpoint}")

    async with create_project(project_endpoint) as project:
        agents = await get_agents_by_name(project, "bing-grounding-agent")

        print(f"There are {len(agents)} to remove:")
        for idx, agent in enumerate(agents, start=1):
            print(f" - {idx}. {agent.id}")

        if (
            agents
            and input(f"Remove all the {len(agents)} agents? [y/N] ") == "y"
        ):
            for idx, agent in enumerate(agents, start=1):
                await project.agents.delete_agent(agent.id)
                print(f" - {idx}. Removed {agent.id}")


if __name__ == "__main__":
    asyncio.run(main())
