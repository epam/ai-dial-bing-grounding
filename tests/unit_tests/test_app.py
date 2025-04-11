import openai


async def test_echo_non_streaming(openai_client: openai.AsyncAzureOpenAI):
    response = await openai_client.chat.completions.create(
        model="whatever",
        stream=False,
        messages=[{"role": "user", "content": "ping"}],
    )

    assert response.choices[0].message.content == "ping"


async def test_echo_streaming(openai_client: openai.AsyncAzureOpenAI):
    response = await openai_client.chat.completions.create(
        model="whatever",
        stream=True,
        messages=[{"role": "user", "content": "ping"}],
    )

    content = ""
    async for chunk in response:
        content += chunk.choices[0].delta.content or ""

    assert content == "ping"
