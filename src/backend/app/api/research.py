"""Research run API endpoints."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.research_run import ResearchRun, ResearchStatus
from app.schemas.research import (
    CreateResearchRunRequest,
    ResearchRun as ResearchRunSchema,
    ResearchRunDetail,
    ResearchRunList,
)
from app.services.research import (
    check_concurrent_run,
    create_research_run,
    execute_research_pipeline,
    get_research_run,
    get_research_run_detail,
)
from app.schemas.molecule import MoleculeList
from app.api.molecules import get_run_molecules

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchRunSchema, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: CreateResearchRunRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new research run.

    Initiates background processing to:
    1. Search PubMed for relevant papers
    2. Extract molecules using Claude LLM
    3. Store results and generate embeddings
    """
    # Check for concurrent runs
    if await check_concurrent_run(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "concurrent_run", "message": "Another research run is already in progress"},
        )

    # Create the run
    run = await create_research_run(db, request.query)
    await db.commit()

    # Schedule background processing
    # Note: We need a new session for background task
    background_tasks.add_task(_run_pipeline_task, run.id)

    return run


async def _run_pipeline_task(run_id: UUID) -> None:
    """Background task to execute the research pipeline."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting background pipeline for run {run_id}")
    print(f"[BACKGROUND] Starting pipeline for run {run_id}", flush=True)

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await execute_research_pipeline(db, run_id)
            await db.commit()
            logger.info(f"Pipeline completed for run {run_id}")
            print(f"[BACKGROUND] Pipeline completed for run {run_id}", flush=True)
        except Exception as e:
            await db.rollback()
            logger.error(f"Pipeline failed for run {run_id}: {e}")
            print(f"[BACKGROUND] Pipeline failed for run {run_id}: {e}", flush=True)


@router.get("/{run_id}", response_model=ResearchRunDetail)
async def get_run(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get research run status and details.

    Returns the run with molecule and paper counts for progress tracking.
    Use this endpoint for polling during processing.
    """
    run, molecule_count, paper_count = await get_research_run_detail(db, run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Research run not found"},
        )

    return ResearchRunDetail(
        id=run.id,
        query=run.query,
        status=run.status.value,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        molecule_count=molecule_count,
        paper_count=paper_count,
    )


@router.get("", response_model=ResearchRunList)
async def list_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
):
    """List research run history.

    Returns runs ordered by creation date (newest first).
    """
    # Validate pagination
    if limit < 1 or limit > 100:
        limit = 20
    if offset < 0:
        offset = 0

    # Get total count
    count_stmt = select(func.count()).select_from(ResearchRun)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Get runs
    stmt = (
        select(ResearchRun)
        .order_by(ResearchRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return ResearchRunList(
        runs=[
            ResearchRunSchema(
                id=run.id,
                query=run.query,
                status=run.status.value,
                created_at=run.created_at,
                updated_at=run.updated_at,
                completed_at=run.completed_at,
                error_message=run.error_message,
            )
            for run in runs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}/molecules", response_model=MoleculeList)
async def get_run_molecules_endpoint(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get molecules discovered in a research run.

    Returns molecules ordered by relevance score (highest first).
    """
    return await get_run_molecules(db, run_id)


@router.post("/{run_id}/retry", response_model=ResearchRunSchema)
async def retry_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retry a failed research run.

    Only failed runs can be retried. The run will be reset to queued status
    and background processing will restart.
    """
    run = await get_research_run(db, run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Research run not found"},
        )

    if run.status != ResearchStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_status", "message": "Only failed runs can be retried"},
        )

    # Reset run status
    run.status = ResearchStatus.QUEUED
    run.error_message = None
    run.completed_at = None
    await db.commit()

    # Schedule background processing
    background_tasks.add_task(_run_pipeline_task, run.id)

    return run
