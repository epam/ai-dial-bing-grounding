from typing import Any, List, Tuple

from aidial_sdk.chat_completion import Choice, Response
from aidial_sdk.exceptions import InternalServerError
from azure.ai.projects.models import (
    AsyncAgentEventHandler,
    MessageDeltaChunk,
    MessageDeltaTextContent,
    MessageDeltaTextUrlCitationAnnotation,
    RunStep,
    RunStepDeltaChunk,
    ThreadMessage,
    ThreadRun,
)


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
                        self.choice.append_content(f"[{idx}]({url}) ")
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
