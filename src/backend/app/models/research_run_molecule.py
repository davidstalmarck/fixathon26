"""ResearchRunMolecule model - junction table linking molecules to research runs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.molecule import SmallMolecule
    from app.models.research_run import ResearchRun


class ResearchRunMolecule(Base):
    """Junction table linking molecules to research runs with relevance scores."""

    __tablename__ = "research_run_molecules"

    research_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    molecule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("small_molecules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    research_run: Mapped["ResearchRun"] = relationship(
        "ResearchRun",
        back_populates="research_run_molecules",
    )
    molecule: Mapped["SmallMolecule"] = relationship(
        "SmallMolecule",
        back_populates="research_run_molecules",
    )
