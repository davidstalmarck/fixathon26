"""Initial schema with pgvector extension and all models.

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Create research_status enum
    op.execute(
        "CREATE TYPE research_status AS ENUM ('queued', 'processing', 'complete', 'failed')"
    )

    # Create research_runs table
    op.create_table(
        "research_runs",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "processing", "complete", "failed", name="research_status"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_research_runs_status", "research_runs", ["status"])
    op.create_index(
        "idx_research_runs_created_at",
        "research_runs",
        [sa.text("created_at DESC")],
    )

    # Create small_molecules table
    op.create_table(
        "small_molecules",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("normalized_name", sa.String(500), nullable=False),
        sa.Column("cas_number", sa.String(50), nullable=True),
        sa.Column("smiles", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="unique_normalized_name"),
        sa.UniqueConstraint("cas_number", name="unique_cas_number"),
    )
    op.execute(
        """
        CREATE INDEX idx_small_molecules_embedding
        ON small_molecules USING hnsw (embedding vector_cosine_ops)
        """
    )

    # Create research_run_molecules junction table
    op.create_table(
        "research_run_molecules",
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("molecule_id", sa.UUID(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["molecule_id"],
            ["small_molecules.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("research_run_id", "molecule_id"),
        sa.CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="check_relevance_score_range",
        ),
    )

    # Create paper_summaries table
    op.create_table(
        "paper_summaries",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("pubmed_id", sa.String(20), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_paper_summaries_run_id", "paper_summaries", ["research_run_id"])
    op.create_index("idx_paper_summaries_pubmed_id", "paper_summaries", ["pubmed_id"])
    op.execute(
        """
        CREATE INDEX idx_paper_summaries_embedding
        ON paper_summaries USING hnsw (embedding vector_cosine_ops)
        """
    )

    # Create molecule_paper_links table
    op.create_table(
        "molecule_paper_links",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("molecule_id", sa.UUID(), nullable=False),
        sa.Column("paper_summary_id", sa.UUID(), nullable=False),
        sa.Column("context_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["molecule_id"],
            ["small_molecules.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paper_summary_id"],
            ["paper_summaries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("molecule_id", "paper_summary_id", name="unique_molecule_paper"),
    )
    op.create_index("idx_molecule_paper_links_molecule", "molecule_paper_links", ["molecule_id"])
    op.create_index("idx_molecule_paper_links_paper", "molecule_paper_links", ["paper_summary_id"])

    # Create updated_at trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """
    )

    # Apply trigger to tables with updated_at
    op.execute(
        """
        CREATE TRIGGER update_research_runs_updated_at
            BEFORE UPDATE ON research_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )
    op.execute(
        """
        CREATE TRIGGER update_small_molecules_updated_at
            BEFORE UPDATE ON small_molecules
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_small_molecules_updated_at ON small_molecules")
    op.execute("DROP TRIGGER IF EXISTS update_research_runs_updated_at ON research_runs")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables in reverse order
    op.drop_table("molecule_paper_links")
    op.drop_table("paper_summaries")
    op.drop_table("research_run_molecules")
    op.drop_table("small_molecules")
    op.drop_table("research_runs")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS research_status")

    # Note: We don't drop the extensions as they might be used by other schemas
