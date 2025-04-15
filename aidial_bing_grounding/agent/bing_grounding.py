import logging
from typing import List

from aidial_sdk.chat_completion import ChatCompletion, Request, Response
from aidial_sdk.exceptions import InternalServerError
from azure.ai.projects.models import ToolDefinition

from aidial_bing_grounding.agent.cache import (
    create_project,
    get_agent,
    get_bing_grounding_tool,
)
from aidial_bing_grounding.agent.event_handler import EventHandler
from aidial_bing_grounding.agent.thread import MessageState, get_thread_id
from aidial_bing_grounding.agent.upstream_config import UpstreamConfiguration
from aidial_bing_grounding.utils.exceptions import dial_exception_decorator
from aidial_bing_grounding.utils.timer import debug_timer

_log = logging.getLogger(__name__)


class BingGroundingApplication(ChatCompletion):
    @dial_exception_decorator
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        conf = UpstreamConfiguration.from_request(request)

        if (conn_string := conf.azure_ai_project_connection_string) is None:
            raise InternalServerError(
                "Connection string for Azure AI Project is missing"
            )

        model_id: str | None = request.original_request.path_params.get(
            "model_id"
        )
        if model_id is None:
            raise InternalServerError("{model_id} path parameter is missing")
        response.set_model(model_id)

        async with create_project(conn_string) as project_client:
            tools: List[ToolDefinition] = []
            if bing := conf.bing_connection_name:
                tool = await get_bing_grounding_tool(project_client, bing)
                tools.extend(tool.definitions)

            async with project_client:
                agent = await get_agent(project_client)
                (
                    thread_id,
                    system_message,
                    new_thread_messages,
                ) = await get_thread_id(project_client, request.messages)

                with debug_timer("response.generate"):
                    with response.create_single_choice() as choice:
                        choice.set_state(
                            MessageState(thread_id=thread_id).dict(
                                exclude_none=True
                            )
                        )

                        async with await project_client.agents.create_stream(
                            thread_id=thread_id,
                            agent_id=agent.id,
                            model=model_id,
                            event_handler=EventHandler(response, choice),
                            max_completion_tokens=request.max_tokens,
                            instructions=system_message,
                            additional_messages=new_thread_messages,
                            # FIXME: add user's tool definitions
                            tools=tools,
                            temperature=request.temperature,
                            top_p=request.top_p,
                        ) as stream:
                            async for event_type, event_data, fun_ret in stream:
                                _log.debug(f"event[{event_type}]: {event_data}")
                                if fun_ret is not None:
                                    raise fun_ret
