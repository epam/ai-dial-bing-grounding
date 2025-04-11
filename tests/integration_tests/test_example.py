import httpx
import pytest


@pytest.mark.asyncio
async def test_example_page_status_code():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.example.com/")
    assert response.status_code == 200
