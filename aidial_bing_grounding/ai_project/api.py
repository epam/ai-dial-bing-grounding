from typing import List

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent

from aidial_bing_grounding.utils.timer import debug_timer


async def get_agents_by_name(
    project_client: AIProjectClient, name: str
) -> List[Agent]:
    after: str | None = None

    ret: List[Agent] = []
    while True:
        with debug_timer("agents.list"):
            agents = await project_client.agents.list_agents(
                limit=10, after=after
            )
        for agent in agents.data:
            if agent.name == name:
                ret.append(agent)
        if not agents.has_more:
            break
        after = agents.last_id

    return ret
