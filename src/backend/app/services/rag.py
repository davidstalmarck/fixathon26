"""RAG service for vector similarity search.

Retrieves relevant papers and molecules from the database using
pgvector cosine similarity search on PubMedBERT embeddings.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.molecule import SmallMolecule
from app.models.paper_summary import PaperSummary
from app.services.embedding import embed_text

# Number of results to return for each type
DEFAULT_PAPER_LIMIT = 5
DEFAULT_MOLECULE_LIMIT = 5


@dataclass
class RetrievedPaper:
    """A paper retrieved via similarity search."""

    id: uuid.UUID
    title: str
    summary: str
    source_url: str | None
    similarity: float


@dataclass
class RetrievedMolecule:
    """A molecule retrieved via similarity search."""

    id: uuid.UUID
    name: str
    description: str | None
    similarity: float


@dataclass
class RAGContext:
    """Context retrieved for RAG response generation."""

    papers: list[RetrievedPaper]
    molecules: list[RetrievedMolecule]

    @property
    def is_empty(self) -> bool:
        """Check if no context was retrieved."""
        return not self.papers and not self.molecules

    def to_prompt_context(self) -> str:
        """Format context for inclusion in LLM prompt."""
        sections = []

        if self.papers:
            sections.append("## Relevant Papers\n")
            for i, paper in enumerate(self.papers, 1):
                sections.append(
                    f"### Paper {i}: {paper.title}\n"
                    f"Similarity: {paper.similarity:.2f}\n"
                    f"Summary: {paper.summary}\n"
                )

        if self.molecules:
            sections.append("## Relevant Molecules\n")
            for i, mol in enumerate(self.molecules, 1):
                desc = mol.description or "No description available"
                sections.append(
                    f"### Molecule {i}: {mol.name}\n"
                    f"Similarity: {mol.similarity:.2f}\n"
                    f"Description: {desc}\n"
                )

        return "\n".join(sections) if sections else "No relevant context found in the database."


async def search_similar_papers(
    db: AsyncSession,
    query_embedding: list[float],
    limit: int = DEFAULT_PAPER_LIMIT,
) -> list[RetrievedPaper]:
    """Search for papers similar to the query embedding.

    Args:
        db: Database session
        query_embedding: 768-dimensional embedding vector
        limit: Maximum number of results

    Returns:
        List of papers ordered by similarity (highest first)
    """
    # Use raw SQL for pgvector cosine similarity
    # The <=> operator computes cosine distance (1 - similarity)
    query = text("""
        SELECT
            id, title, summary, source_url,
            1 - (embedding <=> :embedding) as similarity
        FROM paper_summaries
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :embedding
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {"embedding": str(query_embedding), "limit": limit},
    )
    rows = result.fetchall()

    return [
        RetrievedPaper(
            id=row.id,
            title=row.title,
            summary=row.summary,
            source_url=row.source_url,
            similarity=row.similarity,
        )
        for row in rows
    ]


async def search_similar_molecules(
    db: AsyncSession,
    query_embedding: list[float],
    limit: int = DEFAULT_MOLECULE_LIMIT,
) -> list[RetrievedMolecule]:
    """Search for molecules similar to the query embedding.

    Args:
        db: Database session
        query_embedding: 768-dimensional embedding vector
        limit: Maximum number of results

    Returns:
        List of molecules ordered by similarity (highest first)
    """
    query = text("""
        SELECT
            id, name, description,
            1 - (embedding <=> :embedding) as similarity
        FROM small_molecules
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :embedding
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {"embedding": str(query_embedding), "limit": limit},
    )
    rows = result.fetchall()

    return [
        RetrievedMolecule(
            id=row.id,
            name=row.name,
            description=row.description,
            similarity=row.similarity,
        )
        for row in rows
    ]


async def retrieve_context(
    db: AsyncSession,
    query: str,
    paper_limit: int = DEFAULT_PAPER_LIMIT,
    molecule_limit: int = DEFAULT_MOLECULE_LIMIT,
) -> RAGContext:
    """Retrieve relevant context for a user query.

    Args:
        db: Database session
        query: User's question text
        paper_limit: Max papers to retrieve
        molecule_limit: Max molecules to retrieve

    Returns:
        RAGContext with retrieved papers and molecules
    """
    # Generate embedding for the query
    query_embedding = await embed_text(query)

    if query_embedding is None:
        # If embedding fails, return empty context
        return RAGContext(papers=[], molecules=[])

    # Search for similar papers and molecules in parallel
    papers = await search_similar_papers(db, query_embedding, paper_limit)
    molecules = await search_similar_molecules(db, query_embedding, molecule_limit)

    return RAGContext(papers=papers, molecules=molecules)


async def has_any_data(db: AsyncSession) -> bool:
    """Check if there's any data available for chat.

    Returns True if there are any molecules or papers in the database.
    Chat can still work without embeddings (just without RAG context).
    """
    # Check for any molecules
    mol_query = select(SmallMolecule.id).limit(1)
    mol_result = await db.execute(mol_query)
    if mol_result.scalar() is not None:
        return True

    # Check for any papers
    paper_query = select(PaperSummary.id).limit(1)
    paper_result = await db.execute(paper_query)
    return paper_result.scalar() is not None
