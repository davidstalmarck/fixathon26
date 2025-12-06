"""Chat service for RAG-powered conversations.

Uses Claude API with retrieved context from papers and molecules
to answer user questions with source attribution.
"""

import uuid
from typing import Literal

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.chat import ChatMessage, ChatResponse, ChatSource
from app.services.rag import RAGContext, retrieve_context

settings = get_settings()

# Claude model to use for chat
CHAT_MODEL = "claude-sonnet-4-20250514"

# System prompt for RAG-powered chat
SYSTEM_PROMPT = """You are a scientific research assistant specializing in small molecule research and pharmaceutical compounds.

You have access to a database of scientific papers and molecule information from PubMed research. Use the provided context to answer questions accurately and cite your sources.

IMPORTANT GUIDELINES:
1. Base your answers on the provided context when available
2. If the context doesn't contain relevant information, say so clearly
3. When referencing information from papers or molecules, be specific about which source you're citing
4. Use scientific terminology appropriately but explain complex concepts when needed
5. If asked about something outside your context, acknowledge the limitation
6. Be concise but thorough in your responses

The context below contains relevant papers and molecules retrieved from the database based on the user's question."""


async def generate_chat_response(
    db: AsyncSession,
    message: str,
    history: list[ChatMessage] | None = None,
) -> ChatResponse:
    """Generate a RAG-powered chat response.

    Args:
        db: Database session for RAG retrieval
        message: User's current message
        history: Previous conversation messages (max 10)

    Returns:
        ChatResponse with message and source citations
    """
    # Retrieve relevant context
    context = await retrieve_context(db, message)

    # Build the messages for Claude
    messages = _build_messages(message, history, context)

    # Generate response with Claude
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    # Extract the response text
    response_text = response.content[0].text if response.content else ""

    # Build sources from the context
    sources = _build_sources(context)

    return ChatResponse(
        message=response_text,
        sources=sources,
    )


def _build_messages(
    current_message: str,
    history: list[ChatMessage] | None,
    context: RAGContext,
) -> list[dict]:
    """Build the message list for Claude API.

    Args:
        current_message: User's current question
        history: Previous messages
        context: Retrieved RAG context

    Returns:
        List of message dicts for Claude API
    """
    messages = []

    # Add conversation history if present
    if history:
        for msg in history[-10:]:  # Limit to last 10 messages
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

    # Build the current message with context
    context_text = context.to_prompt_context()
    user_content = f"""<context>
{context_text}
</context>

<question>
{current_message}
</question>

Please answer the question based on the provided context. Cite specific papers or molecules when relevant."""

    messages.append({
        "role": "user",
        "content": user_content,
    })

    return messages


def _build_sources(context: RAGContext) -> list[ChatSource]:
    """Build source citations from RAG context.

    Args:
        context: Retrieved RAG context

    Returns:
        List of ChatSource objects for the response
    """
    sources: list[ChatSource] = []

    # Add paper sources
    for paper in context.papers:
        sources.append(ChatSource(
            type="paper",
            id=paper.id,
            title=paper.title,
            excerpt=paper.summary[:200] + "..." if len(paper.summary) > 200 else paper.summary,
        ))

    # Add molecule sources
    for molecule in context.molecules:
        sources.append(ChatSource(
            type="molecule",
            id=molecule.id,
            title=molecule.name,
            excerpt=molecule.description[:200] + "..." if molecule.description and len(molecule.description) > 200 else molecule.description,
        ))

    return sources
