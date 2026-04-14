import httpx
import openai
from aidial_sdk.utils.merge_chunks import (
    cleanup_indices,
    merge_chat_completion_chunks,
)
from openai import AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

_dummy_response: httpx.Response = httpx.Response(status_code=200)


async def to_block_response(
    response: ChatCompletion | AsyncStream[ChatCompletionChunk],
) -> ChatCompletion:
    if isinstance(response, ChatCompletion):
        return response

    chunks = []
    async for chunk in response:
        body = chunk.dict()
        if "error" in body:
            raise openai.APIStatusError(
                message="Something went wrong",
                response=_dummy_response,
                body=body,
            )
        chunks.append(body)

    response_dict = merge_chat_completion_chunks(*chunks)

    for choice in response_dict["choices"]:
        choice["message"] = cleanup_indices(choice["delta"])
        del choice["delta"]

    response_dict["object"] = "chat.completion"

    return ChatCompletion.parse_obj(response_dict)
