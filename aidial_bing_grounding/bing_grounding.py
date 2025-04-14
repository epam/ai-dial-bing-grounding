import json
import logging
import os
from typing import Any, List, Tuple

from aidial_sdk.chat_completion import (
    ChatCompletion,
    Choice,
    Request,
    Response,
    Role,
)
from aidial_sdk.exceptions import InternalServerError
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    AsyncAgentEventHandler,
    BingGroundingTool,
    MessageDeltaChunk,
    MessageDeltaTextContent,
    MessageDeltaTextUrlCitationAnnotation,
    MessageRole,
    RunStep,
    RunStepDeltaChunk,
    ThreadMessage,
    ThreadRun,
)
from azure.identity.aio import DefaultAzureCredential

from aidial_bing_grounding.utils.errors import UserError
from aidial_bing_grounding.utils.exceptions import dial_exception_decorator

_log = logging.getLogger(__name__)

_UPSTREAM_CONFIG_HEADER_NAME = "x-upstream-extra-data"


class EventHandler(AsyncAgentEventHandler):
    response: Response
    choice: Choice

    citations: List[Tuple[str, str]]

    def __init__(self, response: Response, choice: Choice):
        super().__init__()
        self.choice = choice
        self.response = response
        self.citations = []

    async def on_message_delta(self, delta: MessageDeltaChunk):
        for part in delta.delta.content:
            if (
                isinstance(part, MessageDeltaTextContent)
                and (text_obj := part.text) is not None
            ):
                new_citations = []

                for annotation in text_obj.annotations or []:
                    if isinstance(
                        annotation, MessageDeltaTextUrlCitationAnnotation
                    ):
                        citation = annotation.url_citation
                        new_citations.append((citation.title, citation.url))

                if new_citations:
                    for idx, (title, url) in enumerate(
                        new_citations, start=len(self.citations) + 1
                    ):
                        self.choice.append_content(f"[{idx}]({url})")
                        self.choice.add_attachment(title=title, url=url)
                    self.citations.extend(new_citations)
                else:
                    self.choice.append_content(text_obj.value or "")

    async def on_thread_message(self, message: ThreadMessage):
        pass

    async def on_thread_run(self, run: ThreadRun):
        if (usage := run.usage) is not None:
            self.response.set_usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                # FIXME: prompt_tokens_details aren't in the API
                # but provided by the thread run nonetheless
            )

    async def on_run_step(self, step: RunStep):
        pass

    async def on_run_step_delta(self, delta: RunStepDeltaChunk):
        pass

    async def on_error(self, data: str):
        raise InternalServerError(data)

    async def on_done(self):
        pass

    async def on_unhandled_event(self, event_type: str, event_data: Any):
        raise InternalServerError(f"Unhandled Event Type: {event_type}")


class BingGroundingApplication(ChatCompletion):
    @dial_exception_decorator
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        extra_data = json.loads(
            request.headers.get(_UPSTREAM_CONFIG_HEADER_NAME) or "{}"
        )

        bing_connection_name = (
            extra_data.get("bing_connection_name")
            or os.environ["BING_CONNECTION_NAME"]
        )

        project_connection_string = (
            extra_data.get("project_connection_string")
            or os.environ["PROJECT_CONNECTION_STRING"]
        )

        model_id = request.original_request.path_params["model_id"]

        project_client = AIProjectClient.from_connection_string(  # type: ignore
            credential=DefaultAzureCredential(),
            conn_str=project_connection_string,
        )

        if bing_connection_name:
            bing_connection = await project_client.connections.get(
                connection_name=bing_connection_name
            )
            bing_tool = BingGroundingTool(connection_id=bing_connection.id)
            tools = bing_tool.definitions
        else:
            tools = []

        messages = request.messages

        system_message = None
        if messages and messages[0].role in {Role.SYSTEM, Role.DEVELOPER}:
            # FIXME: support text content parts
            system_message = messages[0].text()
            messages = messages[1:]

        async with project_client:
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

                # FIXME: support content parts
                # FIXME: support message attachments (images)
                await project_client.agents.create_message(
                    thread_id=thread.id,
                    role=message_role,
                    content=message.text(),
                )

            with response.create_single_choice() as choice:
                async with await project_client.agents.create_stream(
                    thread_id=thread.id,
                    agent_id=agent.id,
                    event_handler=EventHandler(response, choice),
                ) as stream:
                    async for event_type, event_data, _ in stream:
                        _log.debug(f"event[{event_type}]: {event_data}")

            await project_client.agents.delete_thread(thread.id)
            await project_client.agents.delete_agent(agent.id)
