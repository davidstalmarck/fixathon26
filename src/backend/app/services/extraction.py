"""Molecule extraction service using Claude LLM.

Extracts small molecule information from paper abstracts using structured prompting.
"""

import json
import re
from dataclasses import dataclass

import anthropic

from app.config import get_settings
from app.services.pubmed import PaperResult

settings = get_settings()


@dataclass
class ExtractedMolecule:
    """Extracted molecule information from a paper."""

    name: str
    normalized_name: str
    cas_number: str | None = None
    smiles: str | None = None
    description: str | None = None
    relevance_score: float = 0.5
    context_excerpt: str | None = None


@dataclass
class ExtractionResult:
    """Result of molecule extraction from a paper."""

    paper_pmid: str
    paper_title: str
    paper_abstract: str
    paper_summary: str
    molecules: list[ExtractedMolecule]


EXTRACTION_SYSTEM_PROMPT = """You are a scientific data extraction specialist focused on small molecules and chemical compounds.

Your task is to analyze scientific paper abstracts and extract:
1. All small molecules, compounds, and chemical substances mentioned
2. Their identifiers (CAS numbers, SMILES notation) if available in the text
3. A brief relevance assessment for the research query

Output Format:
Return a JSON object with:
- "summary": A 2-3 sentence summary of the paper's key findings
- "molecules": An array of extracted molecules with the following fields:
  - "name": The molecule name as mentioned in the paper
  - "cas_number": CAS registry number if mentioned (null otherwise)
  - "smiles": SMILES notation if mentioned (null otherwise)
  - "description": Brief description of the molecule's role/function (1 sentence)
  - "relevance_score": Float from 0.0 to 1.0 indicating relevance to the query
  - "context_excerpt": The sentence or phrase where this molecule was mentioned

Guidelines:
- Extract ALL small molecules, not just the primary ones
- Include metabolites, intermediates, and substrates
- Do not include large molecules like proteins, antibodies, or enzymes
- If no molecules are found, return an empty array
- Be precise with chemical names - maintain exact spelling from the paper"""


class ExtractionService:
    """Service for extracting molecules from paper abstracts."""

    def __init__(self):
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def extract_from_paper(
        self, paper: PaperResult, research_query: str
    ) -> ExtractionResult:
        """Extract molecules from a single paper.

        Args:
            paper: PaperResult with title and abstract
            research_query: The original research query for relevance scoring

        Returns:
            ExtractionResult with summary and extracted molecules
        """
        client = self._get_client()

        user_prompt = f"""Research Query: {research_query}

Paper Title: {paper.title}

Abstract:
{paper.abstract}

Extract all small molecules mentioned in this abstract and assess their relevance to the research query."""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Parse the response
            response_text = message.content[0].text if message.content else "{}"
            extraction_data = self._parse_response(response_text)

            molecules = [
                ExtractedMolecule(
                    name=mol.get("name", ""),
                    normalized_name=self._normalize_name(mol.get("name", "")),
                    cas_number=mol.get("cas_number"),
                    smiles=mol.get("smiles"),
                    description=mol.get("description"),
                    relevance_score=min(max(float(mol.get("relevance_score", 0.5)), 0.0), 1.0),
                    context_excerpt=mol.get("context_excerpt"),
                )
                for mol in extraction_data.get("molecules", [])
                if mol.get("name")
            ]

            return ExtractionResult(
                paper_pmid=paper.pmid,
                paper_title=paper.title,
                paper_abstract=paper.abstract,
                paper_summary=extraction_data.get("summary", ""),
                molecules=molecules,
            )

        except anthropic.APIError as e:
            # Return empty result on API error
            return ExtractionResult(
                paper_pmid=paper.pmid,
                paper_title=paper.title,
                paper_abstract=paper.abstract,
                paper_summary="",
                molecules=[],
            )

    async def extract_from_papers(
        self, papers: list[PaperResult], research_query: str
    ) -> list[ExtractionResult]:
        """Extract molecules from multiple papers.

        Args:
            papers: List of PaperResult objects
            research_query: The original research query

        Returns:
            List of ExtractionResult objects
        """
        results = []
        for paper in papers:
            result = await self.extract_from_paper(paper, research_query)
            results.append(result)
        return results

    def _parse_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response, handling code blocks."""
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```"):
            # Find the end of the code block
            lines = text.split("\n")
            # Skip first line (```json) and last line (```)
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                if line.strip() == "```":
                    break
                if in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"summary": "", "molecules": []}

    def _normalize_name(self, name: str) -> str:
        """Normalize molecule name for deduplication."""
        if not name:
            return ""
        # Lowercase, strip whitespace, remove common variations
        normalized = name.lower().strip()
        # Remove common prefixes/suffixes
        normalized = re.sub(r"^(l-|d-|dl-|\(±\)-|\+/-)", "", normalized)
        # Normalize whitespace
        normalized = " ".join(normalized.split())
        return normalized


# Module-level service instance
_service: ExtractionService | None = None


def get_extraction_service() -> ExtractionService:
    """Get the shared extraction service instance."""
    global _service
    if _service is None:
        _service = ExtractionService()
    return _service


async def extract_molecules(
    papers: list[PaperResult], research_query: str
) -> list[ExtractionResult]:
    """Extract molecules from papers.

    Args:
        papers: List of PaperResult objects
        research_query: The original research query

    Returns:
        List of ExtractionResult objects
    """
    service = get_extraction_service()
    return await service.extract_from_papers(papers, research_query)
