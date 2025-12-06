"""Molecule API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.molecule import SmallMolecule
from app.models.molecule_paper_link import MoleculePaperLink
from app.models.paper_summary import PaperSummary
from app.models.research_run import ResearchRun
from app.models.research_run_molecule import ResearchRunMolecule
from app.schemas.molecule import (
    HasMoleculesResponse,
    Molecule,
    MoleculeDetail,
    MoleculeList,
)
from app.schemas.paper import PaperSummaryBrief

router = APIRouter(prefix="/molecules", tags=["molecules"])


@router.get("", response_model=HasMoleculesResponse)
async def has_molecules(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Check if any molecules exist in the database.

    Used to enable/disable chat mode on the frontend.
    """
    count_stmt = select(func.count()).select_from(SmallMolecule)
    result = await db.execute(count_stmt)
    count = result.scalar() or 0

    return HasMoleculesResponse(
        has_molecules=count > 0,
        count=count,
    )


@router.get("/{molecule_id}", response_model=MoleculeDetail)
async def get_molecule(
    molecule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get molecule details with linked papers.

    Returns the molecule with all papers that mention it.
    """
    # Get molecule
    stmt = select(SmallMolecule).where(SmallMolecule.id == molecule_id)
    result = await db.execute(stmt)
    molecule = result.scalar_one_or_none()

    if molecule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Molecule not found"},
        )

    # Get linked papers
    papers_stmt = (
        select(PaperSummary, MoleculePaperLink.context_excerpt)
        .join(MoleculePaperLink, PaperSummary.id == MoleculePaperLink.paper_summary_id)
        .where(MoleculePaperLink.molecule_id == molecule_id)
        .order_by(PaperSummary.created_at.desc())
    )
    papers_result = await db.execute(papers_stmt)
    papers_data = papers_result.all()

    linked_papers = [
        PaperSummaryBrief(
            id=paper.id,
            title=paper.title,
            context_excerpt=context_excerpt,
        )
        for paper, context_excerpt in papers_data
    ]

    # Get highest relevance score for this molecule
    relevance_stmt = (
        select(func.max(ResearchRunMolecule.relevance_score))
        .where(ResearchRunMolecule.molecule_id == molecule_id)
    )
    relevance_result = await db.execute(relevance_stmt)
    relevance_score = relevance_result.scalar() or 0.5

    return MoleculeDetail(
        id=molecule.id,
        name=molecule.name,
        cas_number=molecule.cas_number,
        smiles=molecule.smiles,
        description=molecule.description,
        relevance_score=relevance_score,
        linked_papers=linked_papers,
    )


# This endpoint is under /research/{run_id}/molecules but defined in a separate router
# We'll create a helper function that the research router can use


async def get_run_molecules(
    db: AsyncSession,
    run_id: UUID,
) -> MoleculeList:
    """Get molecules discovered in a research run.

    Returns molecules ordered by relevance score (highest first).
    """
    # Verify run exists
    run_stmt = select(ResearchRun).where(ResearchRun.id == run_id)
    run_result = await db.execute(run_stmt)
    run = run_result.scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Research run not found"},
        )

    # Get molecules with relevance scores
    stmt = (
        select(SmallMolecule, ResearchRunMolecule.relevance_score)
        .join(ResearchRunMolecule, SmallMolecule.id == ResearchRunMolecule.molecule_id)
        .where(ResearchRunMolecule.research_run_id == run_id)
        .order_by(ResearchRunMolecule.relevance_score.desc())
    )
    result = await db.execute(stmt)
    molecules_data = result.all()

    molecules = [
        Molecule(
            id=mol.id,
            name=mol.name,
            cas_number=mol.cas_number,
            smiles=mol.smiles,
            description=mol.description,
            relevance_score=relevance,
        )
        for mol, relevance in molecules_data
    ]

    return MoleculeList(molecules=molecules)
