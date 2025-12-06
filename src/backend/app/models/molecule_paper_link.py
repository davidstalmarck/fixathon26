"""MoleculePaperLink model - links molecules to the papers that mention them."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.molecule import SmallMolecule
    from app.models.paper_summary import PaperSummary


class MoleculePaperLink(Base, UUIDMixin):
    """Links molecules to papers that mention them."""

    __tablename__ = "molecule_paper_links"

    molecule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("small_molecules.id", ondelete="CASCADE"),
        nullable=False,
    )
    paper_summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_summaries.id", ondelete="CASCADE"),
        nullable=False,
    )
    context_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    molecule: Mapped["SmallMolecule"] = relationship(
        "SmallMolecule",
        back_populates="paper_links",
    )
    paper_summary: Mapped["PaperSummary"] = relationship(
        "PaperSummary",
        back_populates="molecule_links",
    )

    __table_args__ = (
        UniqueConstraint("molecule_id", "paper_summary_id", name="unique_molecule_paper"),
        Index("idx_molecule_paper_links_molecule", "molecule_id"),
        Index("idx_molecule_paper_links_paper", "paper_summary_id"),
    )
