#!/usr/bin/env python3
"""
Parallel Article Processing with Multi-Stage Claude AI Pipeline
Processes multiple articles concurrently for much faster throughput
"""

import os
import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from xml.etree import ElementTree as ET
from anthropic import AsyncAnthropic
import time

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

# Parallel processing settings
MAX_CONCURRENT_ARTICLES = 5  # Process 5 articles at once, 20 will give you rate limited errors 429
MAX_CONCURRENT_STAGES = 4    # All 4 stages can run in parallel per article


class ParallelArticleProcessor:
    """Process articles in parallel using async Claude API"""

    def __init__(self, api_key: str):
        """Initialize processor with Claude API key"""
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_ARTICLES)

    def extract_pmid_from_filename(self, filename: str) -> Optional[str]:
        """Extract PMID from filename"""
        match = re.search(r'PMID(\d+)', filename)
        return match.group(1) if match else None

    def clean_xml_text(self, xml_path: Path) -> Dict[str, str]:
        """Extract and clean text sections from XML article"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Extract title
            title_elem = root.find('.//article-title')
            title = ""
            if title_elem is not None:
                title_parts = []
                for text in title_elem.itertext():
                    if text.strip():
                        title_parts.append(text.strip())
                title = ' '.join(title_parts)

            # Extract abstract
            abstract_parts = []
            for abstract in root.findall('.//abstract'):
                for elem in abstract.iter():
                    if elem.text and elem.text.strip():
                        abstract_parts.append(elem.text.strip())
                    if elem.tail and elem.tail.strip():
                        abstract_parts.append(elem.tail.strip())
            abstract = ' '.join(abstract_parts)

            # Extract body text
            body_parts = []
            for body in root.findall('.//body'):
                for elem in body.iter():
                    if elem.text and elem.text.strip():
                        body_parts.append(elem.text.strip())
                    if elem.tail and elem.tail.strip():
                        body_parts.append(elem.tail.strip())
            body = ' '.join(body_parts)

            # Clean up whitespace
            title = re.sub(r'\s+', ' ', title).strip()
            abstract = re.sub(r'\s+', ' ', abstract).strip()
            body = re.sub(r'\s+', ' ', body).strip()

            return {'title': title, 'abstract': abstract, 'body': body}

        except Exception as e:
            print(f"    ✗ Error parsing XML: {e}")
            return {'title': '', 'abstract': '', 'body': ''}

    async def stage1_clean_text(self, text_sections: Dict[str, str]) -> str:
        """Stage 1: Clean and prepare text"""
        combined_text = f"""Title: {text_sections['title']}

Abstract:
{text_sections['abstract']}

Full Text:
{text_sections['body']}"""

        max_chars = 300000
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + "\n\n[Article truncated]"

        prompt = """You are a scientific text cleaning assistant. Clean and format this scientific article text.

Remove:
- XML artifacts and encoding issues
- Excessive whitespace and formatting issues
- References to figures/tables that aren't present (e.g., "Figure 1", "Table 2")
- Copyright notices and publication metadata
- Author information blocks

Keep:
- All scientific content
- Chemical names and formulas
- Experimental methods and results
- All measurements and data

Return the cleaned text in a clear, readable format with proper paragraphs. Keep all technical and scientific content intact.

Article text:
""" + combined_text

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"      ✗ Stage 1 error: {e}")
            return combined_text

    async def stage2_comprehensive_summary(self, cleaned_text: str, pmid: str) -> str:
        """Stage 2: Write comprehensive 1-2 page summary"""
        prompt = f"""You are a scientific writer specializing in rumen fermentation and methane reduction research.

Write a comprehensive 1-2 page summary of this scientific article. Your summary should include:

1. **Background & Context**: What problem does this research address?
2. **Research Objectives**: What were the specific goals or hypotheses?
3. **Methods**: What experimental approach was used? (animals, treatments, measurements)
4. **Key Findings**: What were the main results and observations?
5. **Mechanisms**: How do the authors explain the observed effects?
6. **Significance**: Why are these findings important for the field?
7. **Limitations & Future Directions**: Any caveats or suggested next steps?

Write in clear, technical prose suitable for researchers in the field. Focus on scientific accuracy and completeness.

Article text:
{cleaned_text}

PMID: {pmid}

Write your comprehensive summary below:"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"      ✗ Stage 2 error: {e}")
            return ""

    async def stage3_extract_molecules(self, cleaned_text: str) -> List[str]:
        """Stage 3: Extract ALL molecules"""
        prompt = """You are a chemistry expert specializing in identifying chemical compounds in scientific literature.

Your task: Extract EVERY chemical compound, molecule, substrate, additive, or metabolite mentioned in this article.

Include:
- **Chemical names**: nitrate, fumarate, 3-nitrooxypropanol (3-NOP), bromochloromethane, etc.
- **Compound classes**: fatty acids, tannins, saponins, flavonoids, terpenes, quinones, etc.
- **Feed ingredients**: corn silage, alfalfa hay, soybean meal, rice straw, wheat straw, etc.
- **Metabolites**: propionate, butyrate, acetate, lactate, succinate, etc.
- **Gases**: methane, carbon dioxide, hydrogen, hydrogen sulfide, etc.
- **Enzymes**: cellulase, xylanase, lipase, protease, etc.
- **Minerals**: calcium, phosphorus, magnesium, sodium, potassium, etc.
- **Vitamins**: vitamin A, vitamin E, etc.
- **Acids**: acetic acid, propionic acid, butyric acid, lactic acid, etc.
- **Specific compounds**: monensin, lasalocid, etc.

Be EXTREMELY thorough - this is critical data. Scan the entire article carefully.

Return ONLY a JSON array of molecules:
["molecule1", "molecule2", "molecule3", ...]

Article text:
""" + cleaned_text

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            print(f"      ✗ Stage 3 error: {e}")
            return []

    async def stage4_extract_topics_keywords(self, cleaned_text: str, pmid: str) -> Dict:
        """Stage 4: Extract topics and keywords"""
        prompt = f"""You are a research librarian specializing in animal science and rumen microbiology.

Analyze this article and extract:

1. **topics**: 5-8 SHORT topic tags (1-3 words each) that categorize this research
   - Use hyphens for multi-word topics (e.g., "methane-reduction", "in-vitro-fermentation")
   - Focus on: experimental approach, compounds tested, outcomes measured, animal species
   - Examples: "methane-inhibition", "rumen-fermentation", "dairy-cattle", "feed-additives"

2. **keywords**: 10-15 specific scientific keywords or key phrases
   - Use exact terminology from the article
   - Include: methods, measurements, statistical approaches, specific outcomes
   - Examples: "volatile fatty acids", "dry matter digestibility", "gas chromatography"

Return ONLY valid JSON:
{{
  "pmid": "{pmid}",
  "topics": ["topic-1", "topic-2", ...],
  "keywords": ["keyword1", "keyword2", ...]
}}

Article text:
{cleaned_text}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"pmid": pmid, "topics": [], "keywords": []}
        except Exception as e:
            print(f"      ✗ Stage 4 error: {e}")
            return {"pmid": pmid, "topics": [], "keywords": []}

    async def process_article(self, xml_path: Path, article_num: int, total: int) -> Optional[Dict]:
        """Process a single article through all stages in parallel"""

        async with self.semaphore:  # Limit concurrent articles
            pmid = self.extract_pmid_from_filename(xml_path.name)
            if not pmid:
                print(f"[{article_num}/{total}] ✗ Could not extract PMID from: {xml_path.name}")
                return None

            output_file = SUMMARIES_DIR / f"PMID{pmid}_analysis.json"
            if output_file.exists():
                print(f"[{article_num}/{total}] ⏭️  Already processed: PMID {pmid}")
                return None

            print(f"\n[{article_num}/{total}] 🔄 Processing PMID {pmid} ({xml_path.name})")

            # Extract raw text (synchronous)
            text_sections = self.clean_xml_text(xml_path)
            if not text_sections['body'] or len(text_sections['body']) < 500:
                print(f"    ✗ Insufficient text")
                return None

            print(f"    ✓ Extracted text (Title={len(text_sections['title'])}, "
                  f"Abstract={len(text_sections['abstract'])}, Body={len(text_sections['body'])})")

            # Run all 4 stages in parallel!
            print(f"    🚀 Running 4 stages in parallel...")
            start_time = time.time()

            results = await asyncio.gather(
                self.stage1_clean_text(text_sections),
                self.stage2_comprehensive_summary(
                    f"Title: {text_sections['title']}\n\nAbstract: {text_sections['abstract']}\n\n{text_sections['body']}",
                    pmid
                ),
                self.stage3_extract_molecules(
                    f"Title: {text_sections['title']}\n\nAbstract: {text_sections['abstract']}\n\n{text_sections['body']}"
                ),
                self.stage4_extract_topics_keywords(
                    f"Title: {text_sections['title']}\n\nAbstract: {text_sections['abstract']}\n\n{text_sections['body']}",
                    pmid
                ),
                return_exceptions=True
            )

            cleaned_text, summary, molecules, topics_keywords = results
            elapsed = time.time() - start_time

            # Handle any errors
            if isinstance(cleaned_text, Exception):
                cleaned_text = ""
            if isinstance(summary, Exception):
                summary = ""
            if isinstance(molecules, Exception):
                molecules = []
            if isinstance(topics_keywords, Exception):
                topics_keywords = {"pmid": pmid, "topics": [], "keywords": []}

            # Compile results
            result = {
                'pmid': pmid,
                'xml_file': str(xml_path.name),
                'title': text_sections['title'],
                'abstract': text_sections['abstract'],
                'comprehensive_summary': summary,
                'topics': topics_keywords.get('topics', []),
                'keywords': topics_keywords.get('keywords', []),
                'molecules': molecules,
                'text_length': {
                    'title': len(text_sections['title']),
                    'abstract': len(text_sections['abstract']),
                    'body': len(text_sections['body']),
                    'cleaned': len(cleaned_text) if isinstance(cleaned_text, str) else 0
                },
                'processing_time_seconds': round(elapsed, 2)
            }

            # Save result
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"    ✓ Complete in {elapsed:.1f}s | Summary: {len(summary)} chars | "
                  f"Topics: {len(result['topics'])} | Keywords: {len(result['keywords'])} | "
                  f"Molecules: {len(molecules)}")

            return result


async def process_all_articles():
    """Process all articles with parallelization"""
    print("="*80)
    print("Parallel Multi-Stage Article Processing with Claude AI")
    print("="*80 + "\n")

    # Test Claude API
    print("Testing Claude API connection...")
    try:
        test_client = AsyncAnthropic(api_key=CLAUDE_API_KEY)
        test_response = await test_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply: OK"}]
        )
        print(f"✓ Claude API connected\n")
    except Exception as e:
        print(f"✗ Claude API test failed: {e}")
        return

    # Get XML files
    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {XML_DIR}")
        return

    print(f"Found {len(xml_files)} XML files")
    print(f"Processing {MAX_CONCURRENT_ARTICLES} articles in parallel")
    print(f"Each article runs 4 stages concurrently\n")

    # Initialize processor
    processor = ParallelArticleProcessor(api_key=CLAUDE_API_KEY)

    # Process all articles
    start_time = time.time()
    tasks = [
        processor.process_article(xml_path, idx, len(xml_files))
        for idx, xml_path in enumerate(xml_files, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count results
    processed = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    skipped = sum(1 for r in results if r is None)
    errors = sum(1 for r in results if isinstance(r, Exception))

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "="*80)
    print("Processing Complete!")
    print("="*80)
    print(f"Total files: {len(xml_files)}")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print(f"Total time: {elapsed/60:.1f} minutes")
    print(f"Avg per article: {elapsed/len(xml_files):.1f} seconds")
    print(f"\nResults saved to: {SUMMARIES_DIR}/")
    print("="*80)

    # Create index
    print("\nCreating master index...")
    all_analyses = []
    for analysis_file in SUMMARIES_DIR.glob("PMID*_analysis.json"):
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                all_analyses.append(json.load(f))
        except Exception as e:
            print(f"Error loading {analysis_file}: {e}")

    if all_analyses:
        index_file = SUMMARIES_DIR / "all_analyses_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(all_analyses, f, indent=2, ensure_ascii=False)
        print(f"✓ Master index created: {len(all_analyses)} articles")


def main():
    """Main entry point"""
    asyncio.run(process_all_articles())


if __name__ == '__main__':
    main()
