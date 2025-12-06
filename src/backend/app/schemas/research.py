"""Pydantic schemas for research run endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateResearchRunRequest(BaseModel):
    """Request body for creating a research run."""

    query: str = Field(
        ...,
        min_length=10,
        description="Research query describing the problem or topic to investigate",
        examples=["compounds that redirect rumen hydrogen into propionate synthesis"],
    )


class ResearchRun(BaseModel):
    """Research run response."""

    id: UUID
    query: str
    status: Literal["queued", "processing", "complete", "failed"]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ResearchRunDetail(ResearchRun):
    """Research run with additional details."""

    molecule_count: int = Field(alias="moleculeCount")
    paper_count: int = Field(alias="paperCount")


class ResearchRunList(BaseModel):
    """Paginated list of research runs."""

    runs: list[ResearchRun]
    total: int
    limit: int | None = None
    offset: int | None = None
