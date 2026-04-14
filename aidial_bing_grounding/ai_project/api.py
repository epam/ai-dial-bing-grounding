import logging
from typing import List

from azure.ai.agents.models import Agent
from azure.ai.projects.aio import AIProjectClient

from aidial_bing_grounding.utils.timer import debug_timer

_log = logging.getLogger(__name__)


async def get_agents_by_name(
    project_client: AIProjectClient, name: str
) -> List[Agent]:
    ret: List[Agent] = []
    with debug_timer("agents.list"):
        agents = project_client.agents.list_agents(limit=20)
        async for agent in agents:
            if agent.name == name:
                ret.append(agent)
    _log.debug(f"Found {len(ret)} agents with name '{name}'")
    return ret


async def does_thread_exist(
    project_client: AIProjectClient, thread_id: str
) -> bool:
    try:
        await project_client.agents.threads.get(thread_id)
        return True
    except Exception:
        return False
