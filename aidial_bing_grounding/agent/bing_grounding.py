import logging
from typing import List

from aidial_sdk.chat_completion import ChatCompletion, Request, Response, Role
from aidial_sdk.exceptions import InternalServerError
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingTool,
    MessageRole,
    ToolDefinition,
)
from azure.identity.aio import DefaultAzureCredential

from aidial_bing_grounding.agent.event_handler import EventHandler
from aidial_bing_grounding.agent.upstream_config import UpstreamConfiguration
from aidial_bing_grounding.utils.errors import UserError
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

        with debug_timer("project_client.create"):
            project_client = AIProjectClient.from_connection_string(  # type: ignore
                credential=DefaultAzureCredential(),
                conn_str=conn_string,
            )

        async with project_client as project_client:
            tools: List[ToolDefinition] = []
            if bing := conf.bing_connection_name:
                with debug_timer("bing_connection.create"):
                    bing_connection = await project_client.connections.get(
                        connection_name=bing
                    )
                tools.extend(
                    BingGroundingTool(
                        connection_id=bing_connection.id
                    ).definitions
                )

            messages = request.messages

            system_message = None
            if messages and messages[0].role in {Role.SYSTEM, Role.DEVELOPER}:
                # FIXME: support text content parts
                system_message = messages[0].text()
                messages = messages[1:]

            async with project_client:
                with debug_timer("agent.create"):
                    agent = await project_client.agents.create_agent(
                        model=model_id,
                        name="my-assistant",
                        instructions=system_message,
                        # FIXME: add user's tool definitions
                        tools=tools,
                        temperature=request.temperature,
                        top_p=request.top_p,
                        headers={"x-ms-enable-preview": "true"},
                    )

                with debug_timer("thread.create"):
                    # FIXME: creation of the thread from scratch takes a lot of time.
                    # Save thread_id to the response state and reuse it later.
                    # *Attach the request hash to the state too.
                    thread = await project_client.agents.create_thread()

                for message in messages:
                    # FIXME: support tool/function calls
                    match message.role:
                        case Role.ASSISTANT:
                            message_role = MessageRole.AGENT
                        case Role.USER:
                            message_role = MessageRole.USER
                        case _:
                            raise UserError(f"Unsupported role: {message.role}")

                    with debug_timer("message.create"):
                        # FIXME: support content parts
                        # FIXME: support message attachments (images)
                        await project_client.agents.create_message(
                            thread_id=thread.id,
                            role=message_role,
                            content=message.text(),
                        )

                with debug_timer("response.generate"):
                    with response.create_single_choice() as choice:
                        async with await project_client.agents.create_stream(
                            thread_id=thread.id,
                            agent_id=agent.id,
                            event_handler=EventHandler(response, choice),
                            max_completion_tokens=request.max_tokens,
                        ) as stream:
                            async for event_type, event_data, _ in stream:
                                _log.debug(f"event[{event_type}]: {event_data}")

                with debug_timer("thread.delete"):
                    await project_client.agents.delete_thread(thread.id)

                with debug_timer("agent.delete"):
                    await project_client.agents.delete_agent(agent.id)
