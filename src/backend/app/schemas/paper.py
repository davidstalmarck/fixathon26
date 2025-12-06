"""Pydantic schemas for paper summary endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.schemas.molecule import MoleculeBrief


class PaperSummaryBrief(BaseModel):
    """Brief paper summary for molecule detail pages."""

    id: UUID
    title: str
    context_excerpt: str | None = Field(default=None, alias="contextExcerpt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class PaperSummary(BaseModel):
    """Paper summary response."""

    id: UUID
    pubmed_id: str = Field(alias="pubmedId")
    title: str
    summary: str
    source_url: str | None = Field(default=None, alias="sourceUrl")
    tagged_molecules: list["MoleculeBrief"] = Field(default_factory=list, alias="taggedMolecules")

    model_config = {"populate_by_name": True, "from_attributes": True}


class PaperSummaryList(BaseModel):
    """List of paper summaries."""

    summaries: list[PaperSummary]
