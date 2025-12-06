"""Pydantic schemas for API request/response validation."""

from app.schemas.research import (
    CreateResearchRunRequest,
    ResearchRun,
    ResearchRunDetail,
    ResearchRunList,
)
from app.schemas.molecule import (
    Molecule,
    MoleculeBrief,
    MoleculeDetail,
    MoleculeList,
    HasMoleculesResponse,
)
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSource,
)
from app.schemas.paper import (
    PaperSummary,
    PaperSummaryBrief,
    PaperSummaryList,
)

# Rebuild models with forward references now that all types are available
MoleculeDetail.model_rebuild()
PaperSummary.model_rebuild()

__all__ = [
    # Research
    "CreateResearchRunRequest",
    "ResearchRun",
    "ResearchRunDetail",
    "ResearchRunList",
    # Molecule
    "Molecule",
    "MoleculeBrief",
    "MoleculeDetail",
    "MoleculeList",
    "HasMoleculesResponse",
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatSource",
    # Paper
    "PaperSummary",
    "PaperSummaryBrief",
    "PaperSummaryList",
]
