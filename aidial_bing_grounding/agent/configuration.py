from enum import StrEnum

from pydantic import BaseModel, Field


class ThreadManagementStrategy(StrEnum):
    RETAIN = "retain"
    DELETE = "delete"


class BingGroundingConfiguration(BaseModel):
    thread_management_strategy: ThreadManagementStrategy | None = Field(
        default=ThreadManagementStrategy.DELETE,
        description="Strategy for managing threads. 'retain' keeps threads, 'delete' removes them after use.",
    )
