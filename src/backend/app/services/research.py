"""Research orchestration service.

Coordinates the full research pipeline:
PubMed search → molecule extraction → deduplication → storage → embedding generation
"""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.molecule import SmallMolecule
from app.models.molecule_paper_link import MoleculePaperLink
from app.models.paper_summary import PaperSummary
from app.models.research_run import ResearchRun, ResearchStatus
from app.models.research_run_molecule import ResearchRunMolecule
from app.services.embedding import get_embedding_service
from app.services.extraction import ExtractionResult, extract_molecules
from app.services.pubmed import search_pubmed


async def check_concurrent_run(db: AsyncSession) -> bool:
    """Check if there's a research run in progress.

    Returns:
        True if a run is in progress, False otherwise
    """
    stmt = select(ResearchRun).where(
        ResearchRun.status.in_([ResearchStatus.QUEUED, ResearchStatus.PROCESSING])
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def create_research_run(db: AsyncSession, query: str) -> ResearchRun:
    """Create a new research run.

    Args:
        db: Database session
        query: Research query string

    Returns:
        Created ResearchRun object
    """
    run = ResearchRun(query=query, status=ResearchStatus.QUEUED)
    db.add(run)
    await db.flush()
    return run


async def get_research_run(db: AsyncSession, run_id: UUID) -> ResearchRun | None:
    """Get a research run by ID.

    Args:
        db: Database session
        run_id: Research run ID

    Returns:
        ResearchRun object or None if not found
    """
    stmt = select(ResearchRun).where(ResearchRun.id == run_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_research_run_detail(
    db: AsyncSession, run_id: UUID
) -> tuple[ResearchRun | None, int, int]:
    """Get research run with molecule and paper counts.

    Args:
        db: Database session
        run_id: Research run ID

    Returns:
        Tuple of (ResearchRun, molecule_count, paper_count)
    """
    run = await get_research_run(db, run_id)
    if run is None:
        return None, 0, 0

    # Count molecules
    molecule_stmt = (
        select(func.count())
        .select_from(ResearchRunMolecule)
        .where(ResearchRunMolecule.research_run_id == run_id)
    )
    molecule_result = await db.execute(molecule_stmt)
    molecule_count = molecule_result.scalar() or 0

    # Count papers
    paper_stmt = (
        select(func.count())
        .select_from(PaperSummary)
        .where(PaperSummary.research_run_id == run_id)
    )
    paper_result = await db.execute(paper_stmt)
    paper_count = paper_result.scalar() or 0

    return run, molecule_count, paper_count


async def execute_research_pipeline(db: AsyncSession, run_id: UUID) -> None:
    """Execute the full research pipeline.

    This is the main orchestration function that:
    1. Searches PubMed for relevant papers
    2. Extracts molecules using Claude
    3. Deduplicates molecules
    4. Stores results in database
    5. Generates embeddings

    Args:
        db: Database session
        run_id: Research run ID
    """
    # Get the research run
    run = await get_research_run(db, run_id)
    if run is None:
        return

    try:
        # Update status to processing
        run.status = ResearchStatus.PROCESSING
        await db.flush()

        # Step 1: Search PubMed
        papers = await search_pubmed(run.query, max_results=30)
        if not papers:
            run.status = ResearchStatus.COMPLETE
            run.completed_at = datetime.now(timezone.utc)
            await db.flush()
            return

        # Step 2: Extract molecules from papers
        extraction_results = await extract_molecules(papers, run.query)

        # Step 3: Store paper summaries and molecules
        await _store_extraction_results(db, run, extraction_results)

        # Step 4: Generate embeddings (optional, async)
        await _generate_embeddings(db, run_id)

        # Mark as complete
        run.status = ResearchStatus.COMPLETE
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()

    except Exception as e:
        # Mark as failed
        run.status = ResearchStatus.FAILED
        run.error_message = str(e)
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        raise


async def _store_extraction_results(
    db: AsyncSession, run: ResearchRun, results: list[ExtractionResult]
) -> None:
    """Store extraction results in the database.

    Args:
        db: Database session
        run: Research run
        results: List of extraction results from papers
    """
    for result in results:
        # Create paper summary
        paper = PaperSummary(
            research_run_id=run.id,
            pubmed_id=result.paper_pmid,
            title=result.paper_title,
            summary=result.paper_summary or result.paper_abstract[:500],
            source_url=f"https://pubmed.ncbi.nlm.nih.gov/{result.paper_pmid}/",
        )
        db.add(paper)
        await db.flush()

        # Process each molecule
        for extracted in result.molecules:
            # Find or create molecule (deduplication)
            molecule = await _find_or_create_molecule(db, extracted)

            # Link molecule to research run
            await _link_molecule_to_run(db, run.id, molecule.id, extracted.relevance_score)

            # Link molecule to paper
            await _link_molecule_to_paper(
                db, molecule.id, paper.id, extracted.context_excerpt
            )

    await db.flush()


async def _find_or_create_molecule(
    db: AsyncSession, extracted: "ExtractedMolecule"
) -> SmallMolecule:
    """Find existing molecule or create new one.

    Deduplication is done by normalized_name, then by cas_number.
    """
    from app.services.extraction import ExtractedMolecule

    # First, try to find by normalized name
    stmt = select(SmallMolecule).where(
        SmallMolecule.normalized_name == extracted.normalized_name
    )
    result = await db.execute(stmt)
    molecule = result.scalar_one_or_none()

    if molecule is not None:
        return molecule

    # Try to find by CAS number if available
    if extracted.cas_number:
        stmt = select(SmallMolecule).where(
            SmallMolecule.cas_number == extracted.cas_number
        )
        result = await db.execute(stmt)
        molecule = result.scalar_one_or_none()
        if molecule is not None:
            return molecule

    # Create new molecule
    molecule = SmallMolecule(
        name=extracted.name,
        normalized_name=extracted.normalized_name,
        cas_number=extracted.cas_number,
        smiles=extracted.smiles,
        description=extracted.description,
    )
    db.add(molecule)
    await db.flush()
    return molecule


async def _link_molecule_to_run(
    db: AsyncSession, run_id: UUID, molecule_id: UUID, relevance_score: float
) -> None:
    """Link a molecule to a research run with relevance score."""
    # Check if link already exists
    stmt = select(ResearchRunMolecule).where(
        ResearchRunMolecule.research_run_id == run_id,
        ResearchRunMolecule.molecule_id == molecule_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        # Update relevance score if higher
        if relevance_score > existing.relevance_score:
            existing.relevance_score = relevance_score
    else:
        # Create new link
        link = ResearchRunMolecule(
            research_run_id=run_id,
            molecule_id=molecule_id,
            relevance_score=relevance_score,
        )
        db.add(link)

    await db.flush()


async def _link_molecule_to_paper(
    db: AsyncSession, molecule_id: UUID, paper_id: UUID, context_excerpt: str | None
) -> None:
    """Link a molecule to a paper summary."""
    # Check if link already exists
    stmt = select(MoleculePaperLink).where(
        MoleculePaperLink.molecule_id == molecule_id,
        MoleculePaperLink.paper_summary_id == paper_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        link = MoleculePaperLink(
            molecule_id=molecule_id,
            paper_summary_id=paper_id,
            context_excerpt=context_excerpt,
        )
        db.add(link)
        await db.flush()


async def _generate_embeddings(db: AsyncSession, run_id: UUID) -> None:
    """Generate embeddings for papers and molecules from a run.

    This is optional and won't fail the pipeline if Modal is not configured.
    """
    try:
        service = await get_embedding_service()

        # Get papers without embeddings
        paper_stmt = select(PaperSummary).where(
            PaperSummary.research_run_id == run_id,
            PaperSummary.embedding.is_(None),
        )
        paper_result = await db.execute(paper_stmt)
        papers = paper_result.scalars().all()

        # Generate paper embeddings
        for paper in papers:
            embedding = await service.embed_paper_summary(paper.title, paper.summary)
            if embedding:
                paper.embedding = embedding

        # Get molecules from this run without embeddings
        mol_stmt = (
            select(SmallMolecule)
            .join(ResearchRunMolecule)
            .where(
                ResearchRunMolecule.research_run_id == run_id,
                SmallMolecule.embedding.is_(None),
            )
        )
        mol_result = await db.execute(mol_stmt)
        molecules = mol_result.scalars().all()

        # Generate molecule embeddings
        for molecule in molecules:
            embedding = await service.embed_molecule(molecule.name, molecule.description)
            if embedding:
                molecule.embedding = embedding

        await db.flush()

    except Exception:
        # Embedding generation is optional, don't fail the pipeline
        pass
