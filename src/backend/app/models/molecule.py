"""SmallMolecule model - a discovered molecule candidate, globally deduplicated."""

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.molecule_paper_link import MoleculePaperLink
    from app.models.research_run_molecule import ResearchRunMolecule


class SmallMolecule(Base, UUIDMixin, TimestampMixin):
    """Small molecule model."""

    __tablename__ = "small_molecules"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    cas_number: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    # Relationships
    research_run_molecules: Mapped[list["ResearchRunMolecule"]] = relationship(
        "ResearchRunMolecule",
        back_populates="molecule",
        cascade="all, delete-orphan",
    )
    paper_links: Mapped[list["MoleculePaperLink"]] = relationship(
        "MoleculePaperLink",
        back_populates="molecule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "idx_small_molecules_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
