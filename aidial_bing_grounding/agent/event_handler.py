from typing import Any, List, Tuple, cast

from aidial_sdk.chat_completion import Choice, Response, Stage
from aidial_sdk.exceptions import HTTPException as DialException
from aidial_sdk.exceptions import InternalServerError
from azure.ai.agents.models import (
    AsyncAgentEventHandler,
    MessageDeltaChunk,
    MessageDeltaTextContent,
    MessageDeltaTextUrlCitationAnnotation,
    RunStep,
    RunStepDeltaChunk,
    RunStepToolCallDetails,
    ThreadMessage,
    ThreadRun,
)


class EventHandler(AsyncAgentEventHandler[DialException | None]):
    response: Response
    choice: Choice

    citations: List[Tuple[str, str]]
    search_stage: Stage | None

    def __init__(self, response: Response, choice: Choice):
        super().__init__()
        self.choice = choice
        self.response = response
        self.citations = []
        self.search_stage = None

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
                        self.choice.append_content(f" [[{idx}]]({url})")
                        self.choice.add_attachment(
                            url=url,
                            title=f"[{idx}] {title}",
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
        if (
            isinstance(sd, RunStepToolCallDetails)
            and step.status == "completed"
        ):
            for tool_call in sd.tool_calls or []:
                if (bg := tool_call.get("bing_grounding")) is not None:
                    if (url := cast(str, bg.get("requesturl"))) is not None:
                        query = url.removeprefix(
                            "https://api.bing.microsoft.com/v7.0/search?q="
                        )
                        self._append_to_search_stage(f"Search query: {query}")

    def _append_to_search_stage(self, content: str):
        if not (stage := self.search_stage):
            stage = self.search_stage = self.choice.create_stage("Bing Search")
            stage.open()
        else:
            content = "\n\n" + content

        stage.append_content(content)

    async def on_run_step_delta(self, delta: RunStepDeltaChunk):
        pass

    async def on_error(self, data: str) -> DialException | None:
        return InternalServerError(data)

    async def on_done(self):
        if self.search_stage:
            self.search_stage.close()

    async def on_unhandled_event(
        self, event_type: str, event_data: Any
    ) -> DialException | None:
        return InternalServerError(f"Unhandled Event Type: {event_type}")
