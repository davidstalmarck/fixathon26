"""PubMed API client using NCBI E-utilities.

Uses ESearch for finding PMIDs and EFetch for retrieving abstracts.
Free API with rate limit of ~3 requests/second.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

from app.config import get_settings

settings = get_settings()

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class PaperResult:
    """Result from PubMed paper retrieval."""

    pmid: str
    title: str
    abstract: str
    source_url: str


class PubMedClient:
    """Client for PubMed E-utilities API."""

    def __init__(self, max_results: int = 30):
        self.max_results = max_results
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, query: str) -> list[str]:
        """Search PubMed for PMIDs matching the query.

        Args:
            query: Search query string

        Returns:
            List of PubMed IDs (PMIDs)
        """
        client = await self._get_client()

        params: dict[str, str | int] = {
            "db": "pubmed",
            "term": query,
            "retmax": self.max_results,
            "retmode": "json",
            "sort": "relevance",
        }

        # Add API key if configured (increases rate limit)
        if settings.pubmed_api_key:
            params["api_key"] = settings.pubmed_api_key

        response = await client.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params=params)
        response.raise_for_status()

        data = response.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])

        return id_list

    async def fetch_papers(self, pmids: list[str]) -> list[PaperResult]:
        """Fetch paper details for the given PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of PaperResult objects with title and abstract
        """
        if not pmids:
            return []

        client = await self._get_client()

        # Fetch in batches to avoid URL length limits
        batch_size = 50
        all_papers = []

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            papers = await self._fetch_batch(client, batch)
            all_papers.extend(papers)

            # Rate limiting: wait between batches
            if i + batch_size < len(pmids):
                await asyncio.sleep(0.4)

        return all_papers

    async def _fetch_batch(
        self, client: httpx.AsyncClient, pmids: list[str]
    ) -> list[PaperResult]:
        """Fetch a batch of papers."""
        params: dict[str, str] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }

        # Add API key if configured
        if settings.pubmed_api_key:
            params["api_key"] = settings.pubmed_api_key

        response = await client.get(f"{PUBMED_BASE_URL}/efetch.fcgi", params=params)
        response.raise_for_status()

        return self._parse_xml_response(response.text)

    def _parse_xml_response(self, xml_text: str) -> list[PaperResult]:
        """Parse PubMed XML response to extract paper data."""
        papers = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return papers

        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            title_elem = article.find(".//ArticleTitle")
            abstract_elem = article.find(".//Abstract/AbstractText")

            if pmid_elem is None or title_elem is None:
                continue

            pmid = pmid_elem.text or ""
            title = self._get_element_text(title_elem)
            abstract = self._get_element_text(abstract_elem) if abstract_elem is not None else ""

            # Skip papers without abstracts
            if not abstract or len(abstract) < 50:
                continue

            papers.append(
                PaperResult(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )

        return papers

    def _get_element_text(self, element: ET.Element | None) -> str:
        """Extract text from XML element, handling mixed content."""
        if element is None:
            return ""

        # Get all text including from child elements
        text_parts = []
        if element.text:
            text_parts.append(element.text)

        for child in element:
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)

        return " ".join(text_parts).strip()

    async def search_and_fetch(self, query: str) -> list[PaperResult]:
        """Search PubMed and fetch paper details in one call.

        Args:
            query: Search query string

        Returns:
            List of PaperResult objects
        """
        pmids = await self.search(query)
        return await self.fetch_papers(pmids)


# Module-level client instance for reuse
_client: PubMedClient | None = None


async def get_pubmed_client() -> PubMedClient:
    """Get the shared PubMed client instance."""
    global _client
    if _client is None:
        _client = PubMedClient()
    return _client


async def search_pubmed(query: str, max_results: int = 30) -> list[PaperResult]:
    """Search PubMed for papers matching the query.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of PaperResult objects with title, abstract, and URL
    """
    client = await get_pubmed_client()
    client.max_results = max_results
    return await client.search_and_fetch(query)
