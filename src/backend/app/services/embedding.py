"""Embedding service for PubMedBERT embeddings via Modal.

Generates 768-dimensional embeddings for papers and molecules using
the PubMedBERT model deployed on Modal infrastructure.
"""

import logging
import modal

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768

# Modal app and class configuration
MODAL_APP_NAME = "jarvis-pubmedbert"
MODAL_CLASS_NAME = "PubMedBERTEmbedder"


class EmbeddingService:
    """Service for generating embeddings via Modal PubMedBERT."""

    def __init__(self):
        self._embedder = None

    def _get_embedder(self):
        """Get or create Modal embedder reference."""
        if self._embedder is None:
            try:
                # Look up the deployed Modal class using from_name
                EmbedderCls = modal.Cls.from_name(MODAL_APP_NAME, MODAL_CLASS_NAME)
                self._embedder = EmbedderCls()
                logger.info(f"Connected to Modal embedder: {MODAL_APP_NAME}/{MODAL_CLASS_NAME}")
            except Exception as e:
                logger.error(f"Failed to connect to Modal embedder: {e}")
                raise
        return self._embedder

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector, or None on error
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else None

    async def generate_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of 768-dimensional embedding vectors (None for failed embeddings)
        """
        if not texts:
            return []

        # If Modal is not configured, return None for all texts
        if not settings.modal_token_id or not settings.modal_token_secret:
            logger.warning("Modal tokens not configured, skipping embeddings")
            return [None] * len(texts)

        try:
            embedder = self._get_embedder()

            # Call generate_embedding for each text
            # The Modal method takes a single string and returns a list[float]
            validated = []
            for text in texts:
                try:
                    result = embedder.generate_embedding.remote(text)
                    if result and len(result) == EMBEDDING_DIMENSION:
                        validated.append(result)
                    else:
                        validated.append(None)
                except Exception as e:
                    logger.warning(f"Failed to embed text: {e}")
                    validated.append(None)

            return validated

        except Exception as e:
            logger.exception(f"Error generating embeddings: {e}")
            return [None] * len(texts)

    async def embed_paper_summary(self, title: str, summary: str) -> list[float] | None:
        """Generate embedding for a paper summary.

        Args:
            title: Paper title
            summary: Paper summary text

        Returns:
            768-dimensional embedding vector
        """
        # Combine title and summary for richer embedding
        text = f"{title}. {summary}"
        return await self.generate_embedding(text)

    async def embed_molecule(
        self, name: str, description: str | None = None
    ) -> list[float] | None:
        """Generate embedding for a molecule.

        Args:
            name: Molecule name
            description: Optional molecule description

        Returns:
            768-dimensional embedding vector
        """
        if description:
            text = f"{name}: {description}"
        else:
            text = name
        return await self.generate_embedding(text)


# Module-level service instance
_service: EmbeddingService | None = None


async def get_embedding_service() -> EmbeddingService:
    """Get the shared embedding service instance."""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


async def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings (768-dim each, or None on error)
    """
    service = await get_embedding_service()
    return await service.generate_embeddings(texts)


async def embed_text(text: str) -> list[float] | None:
    """Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        768-dimensional embedding vector, or None on error
    """
    service = await get_embedding_service()
    return await service.generate_embedding(text)
