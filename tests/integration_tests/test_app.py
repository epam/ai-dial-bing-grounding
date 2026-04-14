import openai
import pytest

from aidial_bing_grounding.agent.upstream_config import UpstreamConfiguration
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
    message_dict = message.dict()

    cc = message_dict.get("custom_content")
    assert cc, "Message custom content is missing"

    attachments = cc.get("attachments")
    assert attachments, "Message attachments are missing"


@pytest.fixture
def no_bing_openai_client(get_openai_client):
    yield get_openai_client(
        headers=UpstreamConfiguration(bing_connection_name="").to_headers()
    )


@pytest.mark.parametrize("stream", [False, True])
async def test_2_plus_3(
    no_bing_openai_client: openai.AsyncAzureOpenAI, stream: bool
):
    response = await no_bing_openai_client.chat.completions.create(
        model="whatever",
        stream=stream,
        temperature=0,
        max_tokens=16,
        messages=[{"role": "user", "content": "2+3=?"}],
    )

    response = await to_block_response(response)

    assert "5" in (response.choices[0].message.content or "")
