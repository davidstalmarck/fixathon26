"""SQLAlchemy models for the molecule research pipeline."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin that adds a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


from app.models.research_run import ResearchRun
from app.models.molecule import SmallMolecule
from app.models.paper_summary import PaperSummary
from app.models.research_run_molecule import ResearchRunMolecule
from app.models.molecule_paper_link import MoleculePaperLink

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "ResearchRun",
    "SmallMolecule",
    "PaperSummary",
    "ResearchRunMolecule",
    "MoleculePaperLink",
]
