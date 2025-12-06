"""PaperSummary model - an extracted summary from a scientific paper."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.molecule_paper_link import MoleculePaperLink
    from app.models.research_run import ResearchRun


class PaperSummary(Base, UUIDMixin):
    """Paper summary model."""

    __tablename__ = "paper_summaries"

    research_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    pubmed_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    research_run: Mapped["ResearchRun"] = relationship(
        "ResearchRun",
        back_populates="paper_summaries",
    )
    molecule_links: Mapped[list["MoleculePaperLink"]] = relationship(
        "MoleculePaperLink",
        back_populates="paper_summary",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_paper_summaries_run_id", "research_run_id"),
        Index("idx_paper_summaries_pubmed_id", "pubmed_id"),
        Index(
            "idx_paper_summaries_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
