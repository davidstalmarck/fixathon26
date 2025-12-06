"""Pydantic schemas for chat endpoints."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., min_length=1, description="User's question")
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=10,
        description="Previous messages for context (max 10)",
    )


class ChatSource(BaseModel):
    """A source used to generate a chat response."""

    type: Literal["paper", "molecule"]
    id: UUID
    title: str = Field(description="Paper title or molecule name")
    excerpt: str | None = Field(default=None, description="Relevant excerpt from source")


class ChatResponse(BaseModel):
    """Chat response with sources."""

    message: str = Field(description="Assistant's response")
    sources: list[ChatSource] = Field(
        default_factory=list,
        description="Papers and molecules used to generate response",
    )
