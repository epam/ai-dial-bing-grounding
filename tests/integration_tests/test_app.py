import openai
import pytest

from tests.utils.chunk import to_block_response


@pytest.mark.parametrize("stream", [False, True])
async def test_bing_search(
    openai_client: openai.AsyncAzureOpenAI, stream: bool
):
    response = await openai_client.chat.completions.create(
        model="whatever",
        stream=stream,
        temperature=0,
        messages=[
            {"role": "user", "content": "What are the latest news in tennis?"}
        ],
    )

    response = await to_block_response(response)

    message = response.choices[0].message

    assert message.dict()["custom_content"]["attachments"]  # type: ignore
