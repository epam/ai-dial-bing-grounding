from enum import StrEnum

from pydantic import BaseModel, Field

from aidial_bing_grounding.utils.env import env_getter


class ThreadManagementStrategy(StrEnum):
    RETAIN = "retain"
    DELETE = "delete"


class BingGroundingConfiguration(BaseModel):
    thread_management_strategy: ThreadManagementStrategy = Field(
        default=ThreadManagementStrategy.DELETE,
        description="Strategy for managing threads. 'retain' keeps threads, 'delete' removes them after use.",
    )
    custom_search_configuration: str | None = Field(
        default_factory=env_getter("BING_CUSTOM_CONFIGURATION"),
        description="Bing Custom Search configuration name",
    )
