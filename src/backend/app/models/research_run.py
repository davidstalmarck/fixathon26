"""ResearchRun model - represents a single research job initiated by a user query."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.paper_summary import PaperSummary
    from app.models.research_run_molecule import ResearchRunMolecule


class ResearchStatus(str, enum.Enum):
    """Status of a research run."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class ResearchRun(Base, UUIDMixin, TimestampMixin):
    """Research run model."""

    __tablename__ = "research_runs"

    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus, name="research_status", create_constraint=True),
        default=ResearchStatus.QUEUED,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    paper_summaries: Mapped[list["PaperSummary"]] = relationship(
        "PaperSummary",
        back_populates="research_run",
        cascade="all, delete-orphan",
    )
    research_run_molecules: Mapped[list["ResearchRunMolecule"]] = relationship(
        "ResearchRunMolecule",
        back_populates="research_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_research_runs_status", "status"),
        Index("idx_research_runs_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
    )
