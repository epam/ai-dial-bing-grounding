from __future__ import annotations

import json
from typing import ClassVar

from aidial_sdk.chat_completion import Request
from pydantic import BaseModel, Field

from aidial_bing_grounding.utils.env import env_getter


class UpstreamConfiguration(BaseModel):
    _UPSTREAM_CONFIG_HEADER_NAME: ClassVar[str] = "x-upstream-extra-data"

    bing_connection_name: str | None = Field(
        default_factory=env_getter("BING_CONNECTION_NAME")
    )
    azure_ai_project_endpoint: str | None = Field(
        default_factory=env_getter("AZURE_AI_PROJECT_ENDPOINT")
    )

    @classmethod
    def from_request(cls, request: Request) -> UpstreamConfiguration:
        conf = request.headers.get(
            UpstreamConfiguration._UPSTREAM_CONFIG_HEADER_NAME
        )
        return UpstreamConfiguration.parse_raw(conf or "{}")

    def to_headers(self) -> dict:
        return {
            UpstreamConfiguration._UPSTREAM_CONFIG_HEADER_NAME: json.dumps(
                self.dict(exclude_none=True)
            )
        }
