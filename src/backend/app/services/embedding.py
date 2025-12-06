"""Embedding service for PubMedBERT embeddings via Modal.

Generates 768-dimensional embeddings for papers and molecules using
the PubMedBERT model deployed on Modal infrastructure.
"""

import httpx

from app.config import get_settings

settings = get_settings()

EMBEDDING_DIMENSION = 768


class EmbeddingService:
    """Service for generating embeddings via Modal PubMedBERT endpoint."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._endpoint_url: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_endpoint_url(self) -> str:
        """Get Modal endpoint URL from config."""
        if self._endpoint_url is None:
            # Modal endpoint format: https://<workspace>--<app>-<function>.modal.run
            # This should be configured via environment variable
            self._endpoint_url = settings.modal_embedding_endpoint
        return self._endpoint_url

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
            return [None] * len(texts)

        try:
            client = await self._get_client()
            endpoint = self._get_endpoint_url()

            # Call Modal endpoint with texts
            response = await client.post(
                endpoint,
                json={"texts": texts},
                headers={
                    "Authorization": f"Bearer {settings.modal_token_secret}",
                },
            )
            response.raise_for_status()

            data = response.json()
            embeddings = data.get("embeddings", [])

            # Validate dimensions
            validated = []
            for emb in embeddings:
                if emb and len(emb) == EMBEDDING_DIMENSION:
                    validated.append(emb)
                else:
                    validated.append(None)

            # Pad with None if fewer embeddings returned
            while len(validated) < len(texts):
                validated.append(None)

            return validated

        except (httpx.HTTPError, KeyError, ValueError):
            # Return None for all texts on error
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
