"""Paper summaries API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.molecule import SmallMolecule
from app.models.molecule_paper_link import MoleculePaperLink
from app.models.paper_summary import PaperSummary
from app.models.research_run import ResearchRun
from app.schemas.molecule import MoleculeBrief
from app.schemas.paper import PaperSummary as PaperSummarySchema, PaperSummaryList

router = APIRouter(prefix="/research", tags=["summaries"])


@router.get("/{run_id}/summaries", response_model=PaperSummaryList)
async def get_run_summaries(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get paper summaries for a research run.

    Returns all paper summaries with their tagged molecules.
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

    # Get paper summaries for this run
    summaries_stmt = (
        select(PaperSummary)
        .where(PaperSummary.research_run_id == run_id)
        .order_by(PaperSummary.created_at.desc())
    )
    summaries_result = await db.execute(summaries_stmt)
    paper_summaries = summaries_result.scalars().all()

    # Build response with tagged molecules for each summary
    summaries_response = []
    for paper in paper_summaries:
        # Get molecules tagged in this paper
        molecules_stmt = (
            select(SmallMolecule)
            .join(MoleculePaperLink, SmallMolecule.id == MoleculePaperLink.molecule_id)
            .where(MoleculePaperLink.paper_summary_id == paper.id)
            .order_by(SmallMolecule.name)
        )
        molecules_result = await db.execute(molecules_stmt)
        tagged_molecules = molecules_result.scalars().all()

        summaries_response.append(
            PaperSummarySchema(
                id=paper.id,
                pubmed_id=paper.pubmed_id,
                title=paper.title,
                summary=paper.summary,
                source_url=paper.source_url,
                tagged_molecules=[
                    MoleculeBrief(id=mol.id, name=mol.name)
                    for mol in tagged_molecules
                ],
            )
        )

    return PaperSummaryList(summaries=summaries_response)
