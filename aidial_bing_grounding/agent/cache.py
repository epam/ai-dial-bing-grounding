from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent, BingGroundingTool
from azure.identity.aio import DefaultAzureCredential
from pydantic import BaseModel

from aidial_bing_grounding.utils.timer import debug_timer


def create_project(conn_string: str) -> AIProjectClient:
    return AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_string,
    )


async def _get_agent_by_name(
    project_client: AIProjectClient, name: str
) -> Agent | None:
    after: str | None = None

    while True:
        with debug_timer("agents.list"):
            agents = await project_client.agents.list_agents(
                limit=10, after=after
            )
        for agent in agents.data:
            if agent.name == name:
                return agent
        if not agents.has_more:
            return None
        after = agents.last_id


class AgentCache(BaseModel):
    _cache: Agent | None = None

    _AGENT_NAME: str = "bing-grounding-agent"

    @staticmethod
    async def _create_agent(project_client: AIProjectClient) -> Agent:
        agent = await _get_agent_by_name(project_client, AgentCache._AGENT_NAME)
        if agent is not None:
            return agent

        with debug_timer("agent.create"):
            # FIXME: add a background job to cleanup unused agents and threads
            # save TTL in the metadata along with the owner name.
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


class BingGroundingToolCache(BaseModel):
    _cache: BingGroundingTool | None = None

    @classmethod
    async def create_bing_grounding_tool(
        cls, project_client: AIProjectClient, bing_connection_name: str
    ) -> BingGroundingTool:
        if cls._cache is None:
            with debug_timer("bing_connection.get"):
                bing_connection = await project_client.connections.get(
                    connection_name=bing_connection_name
                )
            cls._cache = BingGroundingTool(connection_id=bing_connection.id)
        return cls._cache


get_agent = AgentCache.get_agent
get_bing_grounding_tool = BingGroundingToolCache.create_bing_grounding_tool
