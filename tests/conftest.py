import httpx
import openai
import pytest


@pytest.fixture
async def http_client():
    from aidial_bing_grounding.app import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),  # type: ignore
        base_url="http://test-app.com",
        params={"api-version": "dummy-version"},
        headers={"api-key": "dummy-key"},
    ) as client:
        yield client


@pytest.fixture
def openai_client(http_client: httpx.AsyncClient):
    yield openai.AsyncAzureOpenAI(
        azure_endpoint=str(http_client.base_url),
        azure_deployment="gpt-4o",
        api_version="dummy-version",
        api_key="dummy-key",
        max_retries=2,
        timeout=30,
        http_client=http_client,
    )
