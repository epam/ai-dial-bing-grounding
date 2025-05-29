import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Tuple

from aidial_sdk.chat_completion import (
    Choice,
    Message,
    MessageContentTextPart,
    Role,
)
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import MessageRole, ThreadMessageOptions
from azure.core.exceptions import HttpResponseError
from pydantic import BaseModel

from aidial_bing_grounding.agent.configuration import ThreadManagementStrategy
from aidial_bing_grounding.ai_project.api import does_thread_exist
from aidial_bing_grounding.utils.errors import UserError
from aidial_bing_grounding.utils.timer import debug_timer

_log = logging.getLogger(__name__)


class MessageState(BaseModel):
    thread_id: str
    prefix_hash: str | None = None


def _get_last_message_state(
    messages: List[Message],
) -> Tuple[MessageState, int] | None:
    n = len(messages)
    for i in range(n - 1, -1, -1):
        if (cc := messages[i].custom_content) and (state := cc.state):
            try:
                return MessageState.parse_obj(state), i
            except Exception:
                _log.error("Unable to parse message state")
    return None


def _get_message_text_content(message: Message) -> str | None:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        ret = ""
        for part in content:
            if isinstance(part, MessageContentTextPart):
                ret += part.text
            else:
                raise UserError("Non-text messages aren't supported")
        return ret
    return content


def _extract_system_message(
    messages: List[Message],
) -> Tuple[str | None, List[Message]]:
    sys: str | None = None
    i = 0
    while i < len(messages):
        if messages[i].role in {Role.SYSTEM, Role.DEVELOPER}:
            if text := _get_message_text_content(messages[i]):
                if sys:
                    sys = sys + "\n\n" + text
                else:
                    sys = text
            i += 1
        else:
            break

    return sys, messages[i:]


def _create_messages(messages: List[Message]) -> List[ThreadMessageOptions]:
    ret: List[ThreadMessageOptions] = []
    for message in messages:
        # FIXME: support tool/function calls
        # FIXME: support image attachments
        match message.role:
            case Role.ASSISTANT:
                message_role = MessageRole.AGENT
            case Role.USER:
                message_role = MessageRole.USER
            case _:
                raise UserError(
                    f"Unsupported message role: {message.role.value!r}"
                )
        ret.append(
            ThreadMessageOptions(role=message_role, content=message.text())
        )

    return ret


@asynccontextmanager
async def get_thread_id(
    choice: Choice,
    project_client: AIProjectClient,
    messages: List[Message],
    thread_management_strategy: ThreadManagementStrategy,
) -> AsyncGenerator[Tuple[str, str | None, List[ThreadMessageOptions]]]:
    # FIXME: compute prefix hash

    system_message, messages = _extract_system_message(messages)
    thread_messages = _create_messages(messages)

    if (state := _get_last_message_state(messages)) is not None:
        (state, last_thread_message_idx) = state
        thread_messages = thread_messages[last_thread_message_idx + 1 :]
        thread_id = state.thread_id
        if await does_thread_exist(project_client, thread_id):
            # FIXME: still there is no guarantee the thread won't be removed
            # before it's used.
            yield thread_id, system_message, thread_messages

    with debug_timer("thread.create"):
        thread = await project_client.agents.create_thread()

    yield thread.id, system_message, thread_messages

    if thread_management_strategy == ThreadManagementStrategy.DELETE:
        _log.debug(f"Deleting thread {thread.id}")
        try:
            await project_client.agents.delete_thread(thread.id)
        except HttpResponseError as e:
            _log.exception(
                f"Exception while deleting thread {thread.id}: {type(e).__module__}.{type(e).__name__} - {e.message}"
            )
    elif thread_management_strategy == ThreadManagementStrategy.RETAIN:
        _log.debug(f"Retaining thread {thread.id}")
        choice.set_state(
            MessageState(thread_id=thread.id).dict(exclude_none=True)
        )
    else:
        raise UserError(
            f"Unsupported thread retention strategy: {thread_management_strategy.value!r}"
        )
