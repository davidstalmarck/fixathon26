"""Chat API endpoint for RAG-powered conversations."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import generate_chat_response
from app.services.rag import has_any_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Send a chat message and receive a RAG-powered response.

    The response includes source citations from papers and molecules
    that were used to generate the answer.

    Args:
        request: Chat request with message and optional history

    Returns:
        ChatResponse with assistant message and source citations
    """
    # Check if we have any data to chat about
    has_data = await has_any_data(db)
    if not has_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "no_data",
                "message": "No research data available. Please run a research query first.",
            },
        )

    try:
        response = await generate_chat_response(
            db=db,
            message=request.message,
            history=request.history if request.history else None,
        )
        return response
    except Exception as e:
        logger.exception("Error generating chat response")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "chat_error",
                "message": f"Failed to generate response: {str(e)}",
            },
        )
