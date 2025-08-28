import logging

from azure.ai.agents.models import (
    Agent,
    BingCustomSearchTool,
    BingGroundingTool,
)
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from pydantic import BaseModel

from aidial_bing_grounding.ai_project.api import get_agents_by_name
from aidial_bing_grounding.utils.timer import debug_timer

_log = logging.getLogger(__name__)


def create_project(project_endpoint: str) -> AIProjectClient:
    return AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=project_endpoint,
    )


class AgentCache(BaseModel):
    _cache: Agent | None = None

    _AGENT_NAME: str = "bing-grounding-agent"

    @staticmethod
    async def _create_agent(project_client: AIProjectClient) -> Agent:
        agents = await get_agents_by_name(
            project_client, AgentCache._AGENT_NAME
        )
        if agents:
            agent = agents[0]
            _log.debug(f"reused existing agent: {agent.id}")
            return agent

        with debug_timer("agent.create"):
            # FIXME: add a background job to cleanup unused agents and threads
            # save TTL in the metadata along with the owner name.
            # NOTE: I didn't find an API for listing all threads.
            # NOTE: thread has expiration date on their own
            return await project_client.agents.create_agent(
                model="gpt-4o",
                name=AgentCache._AGENT_NAME,
                headers={"x-ms-enable-preview": "true"},
            )

    @classmethod
    async def get_agent(cls, project_client: AIProjectClient) -> Agent:
        cls._cache = cls._cache or await AgentCache._create_agent(
            project_client
        )
        return cls._cache

    @classmethod
    def invalidate(cls):
        cls._cache = None


class BingGroundingToolCache(BaseModel):
    _cache: BingGroundingTool | None = None

    @classmethod
    async def create_bing_grounding_tool(
        cls, project_client: AIProjectClient, bing_connection_name: str
    ) -> BingGroundingTool:
        if cls._cache is None:
            with debug_timer("bing_connection.get"):
                bing_connection = await project_client.connections.get(
                    name=bing_connection_name
                )
            cls._cache = BingGroundingTool(connection_id=bing_connection.id)
        return cls._cache

    @classmethod
    def invalidate(cls):
        cls._cache = None


class BingCustomSearchToolCache(BaseModel):
    _cache: dict[str, BingCustomSearchTool] = {}

    @classmethod
    async def create_bing_custom_search_tool(
        cls,
        project_client: AIProjectClient,
        custom_search_connection_name: str,
        configuration: str,
    ) -> BingCustomSearchTool:
        if tool := cls._cache.get(configuration):
            return tool
        with debug_timer("bing_custom_search_connection.get"):
            custom_search_connection = await project_client.connections.get(
                name=custom_search_connection_name,
            )
        tool = BingCustomSearchTool(
            connection_id=custom_search_connection.id,
            instance_name=configuration,
        )
        cls._cache[configuration] = tool
        return tool

    @classmethod
    def invalidate(cls):
        cls._cache.clear()


get_agent = AgentCache.get_agent
get_bing_grounding_tool = BingGroundingToolCache.create_bing_grounding_tool
get_bing_custom_search_tool = (
    BingCustomSearchToolCache.create_bing_custom_search_tool
)


def invalidate_caches():
    _log.info("Invalidating caches")
    AgentCache.invalidate()
    BingGroundingToolCache.invalidate()
    BingCustomSearchToolCache.invalidate()
