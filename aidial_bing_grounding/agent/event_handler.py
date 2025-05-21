import logging
from typing import Any, Dict, List, Tuple

from aidial_sdk.chat_completion import Choice, Response, Stage
from aidial_sdk.exceptions import HTTPException as DialException
from aidial_sdk.exceptions import InternalServerError
from azure.ai.projects.models import (
    AsyncAgentEventHandler,
    MessageDeltaChunk,
    MessageDeltaTextContent,
    MessageDeltaTextUrlCitationAnnotation,
    RunStep,
    RunStepDeltaChunk,
    RunStepDeltaToolCallObject,
    RunStepToolCallDetails,
    ThreadMessage,
    ThreadRun,
)

_log = logging.getLogger(__name__)


class EventHandler(AsyncAgentEventHandler[DialException | None]):
    response: Response
    choice: Choice
    tool_calls: Dict[int, Stage]

    citations: List[Tuple[str, str]]

    def __init__(self, response: Response, choice: Choice):
        super().__init__()
        self.choice = choice
        self.response = response
        self.citations = []
        self.tool_calls = {}

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
                        self.choice.append_content(f"[\[{idx}\]]({url})")
                        self.choice.add_attachment(
                            data="",
                            title=title,
                            reference_url=url,
                            type="text/markdown",
                        )
                    self.citations.extend(new_citations)
                else:
                    self.choice.append_content(text_obj.value or "")

    async def on_thread_message(self, message: ThreadMessage):
        pass

    async def on_thread_run(self, run: ThreadRun) -> DialException | None:
        if run.status == "failed":
            error = run.last_error
            return InternalServerError(message=error.message, code=error.code)

        if (usage := run.usage) is not None:
            self.response.set_usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                # FIXME: prompt_tokens_details aren't in the API
                # but provided by the thread run nonetheless
            )

    async def on_run_step(self, step: RunStep):
        sd = step.step_details
        if isinstance(sd, RunStepToolCallDetails):
            for idx, tool_call in enumerate(sd.tool_calls or []):
                if (bg := tool_call.get("bing_grounding")) is not None:
                    if (url := bg.get("requesturl")) is not None:
                        self._append_to_stage("Bing Search", idx, url)
                        self._close_stage(idx)

    def _append_to_stage(self, title: str, idx: int, content: str):
        if not (stage := self.tool_calls.get(idx)):
            stage = self.tool_calls[idx] = self.choice.create_stage(title)
            stage.open()
        stage.append_content(content)

    def _close_stage(self, idx: int):
        self.tool_calls[idx].close()

    async def on_run_step_delta(self, delta: RunStepDeltaChunk):
        sd = delta.delta.step_details
        if isinstance(sd, RunStepDeltaToolCallObject):
            for tool_call in sd.tool_calls or []:
                idx = tool_call.index
                if (bg := tool_call.get("bing_grounding")) is not None:
                    if (url := bg.get("requesturl")) is not None:
                        self._append_to_stage("Bing Search", idx, url)

    async def on_error(self, data: str) -> DialException | None:
        return InternalServerError(data)

    async def on_done(self):
        pass

    async def on_unhandled_event(
        self, event_type: str, event_data: Any
    ) -> DialException | None:
        return InternalServerError(f"Unhandled Event Type: {event_type}")
