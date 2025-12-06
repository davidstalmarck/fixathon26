"""Pydantic schemas for molecule endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.schemas.paper import PaperSummaryBrief


class MoleculeBrief(BaseModel):
    """Brief molecule info for tags and lists."""

    id: UUID
    name: str


class Molecule(BaseModel):
    """Molecule response with relevance score."""

    id: UUID
    name: str
    cas_number: str | None = Field(default=None, alias="casNumber")
    smiles: str | None = None
    description: str | None = None
    relevance_score: float = Field(alias="relevanceScore")

    model_config = {"populate_by_name": True, "from_attributes": True}


class MoleculeDetail(Molecule):
    """Molecule with linked papers."""

    linked_papers: list["PaperSummaryBrief"] = Field(alias="linkedPapers")


class MoleculeList(BaseModel):
    """List of molecules."""

    molecules: list[Molecule]


class HasMoleculesResponse(BaseModel):
    """Response for checking if molecules exist."""

    has_molecules: bool = Field(alias="hasMolecules")
    count: int

    model_config = {"populate_by_name": True}
