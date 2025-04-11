from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from aidial_bing_grounding.utils.list import get_last


class SampleApplication(ChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        with response.create_single_choice() as choice:
            choice.append_content(get_last(request.messages).text())
