#!/usr/bin/env python3
"""
Process Articles with Claude AI
Extract summaries, topics, keywords, and molecules from full-text articles
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from xml.etree import ElementTree as ET
import anthropic

# Load environment variables
load_dotenv()

# Directories
XML_DIR = Path("pubmed-articles/xmls")
SUMMARIES_DIR = Path("pubmed-articles/summaries")
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

# Claude API setup
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY not found in .env file")


class ArticleProcessor:
    """Process articles using Claude AI to extract structured information"""

    def __init__(self, api_key: str):
        """Initialize processor with Claude API key"""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4

    def clean_xml_text(self, xml_path: Path) -> str:
        """
        Extract and clean text from XML article

        Args:
            xml_path: Path to XML file

        Returns:
            Cleaned text content
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Extract title
            title_elem = root.find('.//article-title')
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            # Extract abstract
            abstract_parts = []
            for abstract in root.findall('.//abstract'):
                for elem in abstract.iter():
                    if elem.text:
                        abstract_parts.append(elem.text.strip())
                    if elem.tail:
                        abstract_parts.append(elem.tail.strip())
            abstract = ' '.join(abstract_parts)

            # Extract body text
            body_parts = []
            for body in root.findall('.//body'):
                for elem in body.iter():
                    if elem.text:
                        body_parts.append(elem.text.strip())
                    if elem.tail:
                        body_parts.append(elem.tail.strip())
            body = ' '.join(body_parts)

            # Combine all text
            full_text = f"Title: {title}\n\nAbstract: {abstract}\n\nBody: {body}"

            # Clean up whitespace
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = re.sub(r'\n\s*\n', '\n\n', full_text)

            return full_text.strip()

        except Exception as e:
            print(f"Error parsing XML {xml_path}: {e}")
            return ""

    def extract_with_claude(self, text: str, pmid: str) -> Dict:
        """
        Use Claude to extract structured information from article text

        Args:
            text: Article full text
            pmid: PubMed ID for reference

        Returns:
            Dictionary with extracted information
        """
        # Truncate if too long (Claude has ~200k token limit)
        max_chars = 400000  # ~100k tokens
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Article truncated due to length]"

        prompt = f"""You are analyzing a scientific article about rumen fermentation and methane reduction. Your task is to extract structured information from this article.

Article text:
{text}

Please analyze this article and provide the following information in JSON format:

1. **summary**: A concise 2-3 sentence summary of the article's main findings and contributions.

2. **topics**: 3-5 short topic tags (1-2 words each) that describe the main themes. Use hyphens for multi-word topics (e.g., "methane-reduction", "rumen-fermentation"). Focus on scientific concepts.

3. **keywords**: 5-10 relevant scientific keywords or key phrases from the article. These should be specific terms used in the research.

4. **molecules**: A comprehensive list of ALL chemical compounds, molecules, substrates, or additives mentioned in the article. This is CRITICAL - include:
   - All chemical names (e.g., "nitrate", "fumarate", "3-NOP")
   - All compound classes (e.g., "fatty acids", "tannins", "flavonoids")
   - All substrates or additives tested (e.g., "corn silage", "soybean meal")
   - All metabolites mentioned (e.g., "propionate", "butyrate", "acetate")
   - Be thorough - this is the most important extraction task

Return ONLY valid JSON in this exact format:
{{
  "pmid": "{pmid}",
  "summary": "...",
  "topics": ["topic-1", "topic-2", "topic-3"],
  "keywords": ["keyword1", "keyword2", ...],
  "molecules": ["molecule1", "molecule2", ...]
}}

Be extremely thorough with the molecules list - scan the entire article carefully."""

        try:
            print(f"  Sending {len(text):,} chars to Claude...")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            print(f"  Received response from Claude ({len(response_text)} chars)")

            # Extract JSON from response (in case Claude adds explanation)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                print(f"  Successfully parsed JSON")
                return result
            else:
                print(f"  ⚠️  Could not parse JSON from Claude response")
                print(f"  Response preview: {response_text[:200]}...")
                return self._create_empty_result(pmid)

        except anthropic.APIError as e:
            print(f"  ✗ Claude API Error: {e}")
            print(f"  Error type: {type(e).__name__}")
            return self._create_empty_result(pmid)
        except Exception as e:
            print(f"  ✗ Unexpected error calling Claude API: {e}")
            print(f"  Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return self._create_empty_result(pmid)

    def _create_empty_result(self, pmid: str) -> Dict:
        """Create empty result structure"""
        return {
            "pmid": pmid,
            "summary": "",
            "topics": [],
            "keywords": [],
            "molecules": []
        }

    def process_article(self, xml_path: Path) -> Optional[Dict]:
        """
        Process a single article XML file

        Args:
            xml_path: Path to XML file

        Returns:
            Extracted information dictionary or None if already processed
        """
        # Extract PMID and PMC ID from filename
        filename = xml_path.stem  # e.g., "PMC12345_PMID67890"
        match = re.search(r'PMC(\d+)_PMID(\d+)', filename)
        if not match:
            print(f"  ✗ Could not extract IDs from filename: {filename}")
            return None

        pmc_id = match.group(1)
        pmid = match.group(2)

        # Check if already processed
        output_file = SUMMARIES_DIR / f"PMID{pmid}_PMC{pmc_id}.json"
        if output_file.exists():
            print(f"  ✓ Already processed, skipping")
            return None

        print(f"\nProcessing PMC{pmc_id} / PMID {pmid}")
        print(f"  XML: {xml_path.name}")

        # Clean and extract text from XML
        print(f"  Extracting text from XML...")
        text = self.clean_xml_text(xml_path)

        if not text or len(text) < 500:
            print(f"  ✗ Text too short or extraction failed ({len(text)} chars)")
            return None

        print(f"  Extracted {len(text):,} characters")

        # Extract information with Claude
        print(f"  Analyzing with Claude...")
        result = self.extract_with_claude(text, pmid)

        # Add metadata
        result['pmc_id'] = pmc_id
        result['xml_file'] = str(xml_path)
        result['text_length'] = len(text)

        # Save result
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"  ✓ Processed successfully")
        print(f"    Summary: {result['summary'][:100]}...")
        print(f"    Topics: {', '.join(result['topics'][:5])}")
        print(f"    Molecules found: {len(result['molecules'])}")
        print(f"    Saved to: {output_file.name}")

        return result


def main():
    """Main processing workflow"""
    print("="*80)
    print("Article Processing Pipeline with Claude AI")
    print("="*80 + "\n")

    # Test Claude API connection
    print("Testing Claude API connection...")
    try:
        test_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        test_response = test_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": "Reply with just 'OK'"}]
        )
        print(f"✓ Claude API connected successfully")
        print(f"  API key: {CLAUDE_API_KEY[:10]}...{CLAUDE_API_KEY[-4:]}\n")
    except Exception as e:
        print(f"✗ Claude API test failed: {e}")
        print(f"  Please check your CLAUDE_API_KEY in .env file")
        return

    # Check for XML files
    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {XML_DIR}")
        print("Please run download_articles.py first to download articles.")
        return

    print(f"Found {len(xml_files)} XML files to process\n")

    # Initialize processor
    processor = ArticleProcessor(api_key=CLAUDE_API_KEY)

    # Process each article
    results = []
    processed_count = 0
    skipped_count = 0
    error_count = 0

    for idx, xml_path in enumerate(xml_files, 1):
        print(f"\n[{idx}/{len(xml_files)}]", end=" ")

        try:
            result = processor.process_article(xml_path)

            if result is None:
                skipped_count += 1
            else:
                results.append(result)
                processed_count += 1

        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            error_count += 1
            continue

        # Save progress every 10 articles
        if idx % 10 == 0:
            progress_file = SUMMARIES_DIR / "processing_progress.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed': processed_count,
                    'skipped': skipped_count,
                    'errors': error_count,
                    'total': len(xml_files)
                }, f, indent=2)
            print(f"\n  Progress saved: {processed_count} processed, {skipped_count} skipped")

    # Final summary
    print("\n" + "="*80)
    print("Processing Summary")
    print("="*80)
    print(f"Total XML files: {len(xml_files)}")
    print(f"Newly processed: {processed_count}")
    print(f"Already processed (skipped): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"\nSummaries saved to: {SUMMARIES_DIR}/")
    print("="*80)

    # Create a combined index of all processed articles
    all_summaries = []
    for summary_file in SUMMARIES_DIR.glob("PMID*.json"):
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                all_summaries.append(json.load(f))
        except Exception as e:
            print(f"Error loading {summary_file}: {e}")

    if all_summaries:
        index_file = SUMMARIES_DIR / "all_summaries_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(all_summaries, f, indent=2, ensure_ascii=False)
        print(f"\nCreated index of all summaries: {index_file}")
        print(f"Total articles in index: {len(all_summaries)}")


if __name__ == '__main__':
    main()