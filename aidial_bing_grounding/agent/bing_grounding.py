import logging
from typing import List, Union

from aidial_sdk.chat_completion import ChatCompletion, Request, Response
from aidial_sdk.deployment.configuration import (
    ConfigurationRequest,
    ConfigurationResponse,
)
from aidial_sdk.exceptions import InternalServerError
from azure.ai.agents.models import ToolDefinition

from aidial_bing_grounding.agent.cache import (
    create_project,
    get_agent,
    get_bing_custom_search_tool,
    get_bing_grounding_tool,
    invalidate_caches,
)
from aidial_bing_grounding.agent.configuration import BingGroundingConfiguration
from aidial_bing_grounding.agent.event_handler import EventHandler
from aidial_bing_grounding.agent.thread import get_thread_id
from aidial_bing_grounding.agent.upstream_config import UpstreamConfiguration
from aidial_bing_grounding.utils.exceptions import dial_exception_decorator
from aidial_bing_grounding.utils.timer import debug_timer

_log = logging.getLogger(__name__)


class BingGroundingApplication(ChatCompletion):
    async def configuration(
        self, request: ConfigurationRequest
    ) -> Union[ConfigurationResponse, dict]:
        return BingGroundingConfiguration.schema()

    @dial_exception_decorator
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        upstream_conf = UpstreamConfiguration.from_request(request)
        config = (
            BingGroundingConfiguration.parse_obj(
                request.custom_fields.configuration
            )
            if request.custom_fields and request.custom_fields.configuration
            else BingGroundingConfiguration()
        )
        _log.debug(
            f"Received request for Bing Grounding with configuration: {config}"
        )

        if (
            project_endpoint := upstream_conf.azure_ai_project_endpoint
        ) is None:
            raise InternalServerError(
                "Connection string for Azure AI Project is missing"
            )

        model_id: str | None = request.original_request.path_params.get(
            "model_id"
        )
        if model_id is None:
            raise InternalServerError("{model_id} path parameter is missing")
        response.set_model(model_id)

        async with create_project(project_endpoint) as project_client:
            tools: List[ToolDefinition] = []
            bing_custom = upstream_conf.bing_custom_connection_name
            bing = upstream_conf.bing_connection_name
            if bing_custom and config.custom_search_configuration:
                tool = await get_bing_custom_search_tool(
                    project_client,
                    bing_custom,
                    config.custom_search_configuration,
                )
                tools.extend(tool.definitions)
            elif bing:
                tool = await get_bing_grounding_tool(project_client, bing)
                tools.extend(tool.definitions)

            async with project_client:
                agent = await get_agent(project_client)

                with response.create_single_choice() as choice:
                    async with get_thread_id(
                        choice,
                        project_client,
                        request.messages,
                        config.thread_management_strategy,
                    ) as thread_data:
                        (
                            thread_id,
                            system_message,
                            new_thread_messages,
                        ) = thread_data

                        with debug_timer("response.generate"):
                            async with await project_client.agents.runs.stream(
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
                                    _log.debug(
                                        f"event[{event_type}]: {event_data}"
                                    )
                                    if fun_ret is not None:
                                        # FIXME: we should rather retry on these error,
                                        # but the choice is already polluted with start-up
                                        # chunks. We need to introduce LazyChoice.
                                        # There is no way to delegate the retry to the client,
                                        # since most likely it's a streaming request.
                                        invalidation_triggers = [
                                            "Bing Search API key is missing for Bing Grounding tool.",
                                            "No assistant found with id",
                                            "No thread found with id",
                                        ]
                                        if any(
                                            [
                                                t in fun_ret.message
                                                for t in invalidation_triggers
                                            ]
                                        ):
                                            invalidate_caches()

                                        raise fun_ret
