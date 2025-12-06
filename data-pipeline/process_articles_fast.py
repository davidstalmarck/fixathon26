#!/usr/bin/env python3
"""
Ultra-Fast Parallel Article Processing
Maximizes CPU usage with aggressive parallelization
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
from concurrent.futures import ThreadPoolExecutor

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

# RATE-LIMIT-AWARE PARALLEL SETTINGS
# Note: Anthropic rate limit is 450K tokens/min
# Each article uses ~150K tokens across 4 stages
# So we can process ~3 articles/min max = process 3 at once
MAX_CONCURRENT_ARTICLES = 3  # Stay within rate limits
MAX_API_CALLS_PER_SECOND = 10  # Reduced to avoid overwhelming API


class UltraFastProcessor:
    """Ultra-fast parallel processor using aggressive concurrency"""

    def __init__(self, api_key: str):
        """Initialize with async client"""
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_ARTICLES)
        self.rate_limiter = asyncio.Semaphore(MAX_API_CALLS_PER_SECOND)

    def extract_pmid_from_filename(self, filename: str) -> Optional[str]:
        """Extract PMID from filename"""
        match = re.search(r'PMID(\d+)', filename)
        return match.group(1) if match else None

    def clean_xml_text(self, xml_path: Path) -> Dict[str, str]:
        """Extract text from XML (runs in thread pool)"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Extract title
            title_elem = root.find('.//article-title')
            title = ""
            if title_elem is not None:
                title_parts = [text.strip() for text in title_elem.itertext() if text.strip()]
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

            # Clean up
            title = re.sub(r'\s+', ' ', title).strip()
            abstract = re.sub(r'\s+', ' ', abstract).strip()
            body = re.sub(r'\s+', ' ', body).strip()

            return {'title': title, 'abstract': abstract, 'body': body}

        except Exception as e:
            return {'title': '', 'abstract': '', 'body': ''}

    async def call_claude(self, prompt: str, max_tokens: int = 4096, max_retries: int = 3) -> str:
        """Make rate-limited Claude API call with retry logic"""
        async with self.rate_limiter:
            for attempt in range(max_retries):
                try:
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "rate_limit" in error_str.lower():
                        if attempt < max_retries - 1:
                            # Exponential backoff: wait 10s, 20s, 40s
                            wait_time = 10 * (2 ** attempt)
                            print(f"    Rate limit hit, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    # For other errors or final retry, just return empty
                    print(f"    API Error: {error_str[:200]}")
                    return ""
            return ""

    async def stage1_clean_text(self, text: str) -> str:
        """Stage 1: Clean text"""
        if len(text) > 300000:
            text = text[:300000] + "\n\n[Truncated]"

        prompt = f"""Clean this scientific article text. Remove XML artifacts, fix formatting, keep all scientific content.

Article: {text}"""

        return await self.call_claude(prompt, max_tokens=8192)

    async def stage2_summary(self, text: str, pmid: str) -> str:
        """Stage 2: Comprehensive summary"""
        prompt = f"""Write a comprehensive 1-2 page scientific summary covering: Background, Objectives, Methods, Findings, Mechanisms, Significance, Limitations.

Article: {text}
PMID: {pmid}"""

        return await self.call_claude(prompt, max_tokens=4096)

    async def stage3_molecules(self, text: str) -> List[str]:
        """Stage 3: Extract molecules"""
        prompt = f"""Extract ALL molecules, compounds, chemicals, feeds, metabolites from this article. Return ONLY a JSON array: ["mol1", "mol2", ...]

Article: {text}"""

        response = await self.call_claude(prompt, max_tokens=4096)

        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                return []
        return []

    async def stage4_topics_keywords(self, text: str, pmid: str) -> Dict:
        """Stage 4: Topics and keywords"""
        prompt = f"""Extract 5-8 topic tags and 10-15 keywords. Return ONLY JSON: {{"pmid": "{pmid}", "topics": [...], "keywords": [...]}}

Article: {text}"""

        response = await self.call_claude(prompt, max_tokens=2048)

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                return {"pmid": pmid, "topics": [], "keywords": []}
        return {"pmid": pmid, "topics": [], "keywords": []}

    async def process_article(self, xml_path: Path, idx: int, total: int) -> Optional[Dict]:
        """Process one article with full parallelization"""

        async with self.semaphore:
            pmid = self.extract_pmid_from_filename(xml_path.name)
            if not pmid:
                return None

            output_file = SUMMARIES_DIR / f"PMID{pmid}_analysis.json"
            if output_file.exists():
                print(f"[{idx}/{total}] ⏭️  PMID {pmid}")
                return None

            print(f"[{idx}/{total}] 🔄 PMID {pmid}")
            start = time.time()

            # XML parsing in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            text_sections = await loop.run_in_executor(None, self.clean_xml_text, xml_path)

            if not text_sections['body'] or len(text_sections['body']) < 500:
                return None

            # Prepare full text
            full_text = f"Title: {text_sections['title']}\n\nAbstract: {text_sections['abstract']}\n\n{text_sections['body']}"

            # Run ALL 4 stages in parallel
            cleaned, summary, molecules, topics_kw = await asyncio.gather(
                self.stage1_clean_text(full_text),
                self.stage2_summary(full_text, pmid),
                self.stage3_molecules(full_text),
                self.stage4_topics_keywords(full_text, pmid),
                return_exceptions=True
            )

            # Handle errors
            if isinstance(cleaned, Exception): cleaned = ""
            if isinstance(summary, Exception): summary = ""
            if isinstance(molecules, Exception): molecules = []
            if isinstance(topics_kw, Exception): topics_kw = {"pmid": pmid, "topics": [], "keywords": []}

            # Compile result
            result = {
                'pmid': pmid,
                'xml_file': xml_path.name,
                'title': text_sections['title'],
                'abstract': text_sections['abstract'],
                'comprehensive_summary': summary,
                'topics': topics_kw.get('topics', []),
                'keywords': topics_kw.get('keywords', []),
                'molecules': molecules,
                'text_length': {
                    'title': len(text_sections['title']),
                    'abstract': len(text_sections['abstract']),
                    'body': len(text_sections['body']),
                    'cleaned': len(cleaned) if isinstance(cleaned, str) else 0
                },
                'processing_time_seconds': round(time.time() - start, 2)
            }

            # Save (in thread pool to not block)
            def save_result():
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

            await loop.run_in_executor(None, save_result)

            elapsed = time.time() - start
            print(f"    ✓ {elapsed:.1f}s | Summary: {len(summary)} | Topics: {len(result['topics'])} | "
                  f"Keywords: {len(result['keywords'])} | Molecules: {len(molecules)}")

            return result


async def process_batch(xml_files: List[Path], batch_start: int):
    """Process a batch of articles"""
    processor = UltraFastProcessor(api_key=CLAUDE_API_KEY)

    tasks = [
        processor.process_article(xml_path, batch_start + idx, len(xml_files))
        for idx, xml_path in enumerate(xml_files)
    ]

    return await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    """Main processing with batched execution"""
    print("="*80)
    print("ULTRA-FAST Parallel Article Processing")
    print(f"Using {MAX_CONCURRENT_ARTICLES} concurrent articles")
    print("="*80 + "\n")

    # Test API
    print("Testing Claude API...")
    try:
        test_client = AsyncAnthropic(api_key=CLAUDE_API_KEY)
        await test_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "OK"}]
        )
        print("✓ API connected\n")
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return

    # Get files
    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        print(f"No XML files in {XML_DIR}")
        return

    print(f"Found {len(xml_files)} XML files")
    print(f"Processing {MAX_CONCURRENT_ARTICLES} at once")
    print(f"All 4 stages run in parallel per article\n")

    start_time = time.time()

    # Process in large batches for maximum parallelism
    BATCH_SIZE = 100  # Process 100 files at a time
    all_results = []

    for i in range(0, len(xml_files), BATCH_SIZE):
        batch = xml_files[i:i+BATCH_SIZE]
        print(f"\n{'='*80}")
        print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(xml_files)-1)//BATCH_SIZE + 1}")
        print(f"{'='*80}")

        batch_results = await process_batch(batch, i)
        all_results.extend(batch_results)

        # Quick progress save
        processed = sum(1 for r in all_results if r and not isinstance(r, Exception))
        skipped = sum(1 for r in all_results if r is None)

        print(f"\nBatch complete | Processed: {processed} | Skipped: {skipped}")

    # Final stats
    elapsed = time.time() - start_time
    processed = sum(1 for r in all_results if r and not isinstance(r, Exception))
    skipped = sum(1 for r in all_results if r is None)
    errors = sum(1 for r in all_results if isinstance(r, Exception))

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"Total: {len(xml_files)} | Processed: {processed} | Skipped: {skipped} | Errors: {errors}")
    print(f"Time: {elapsed/60:.1f} min | Avg: {elapsed/len(xml_files):.1f}s per article")
    print(f"Throughput: {len(xml_files)/elapsed*60:.1f} articles/min")
    print("="*80)

    # Create index
    print("\nCreating index...")
    all_analyses = []
    for f in SUMMARIES_DIR.glob("PMID*_analysis.json"):
        try:
            with open(f, 'r') as fp:
                all_analyses.append(json.load(fp))
        except:
            pass

    if all_analyses:
        with open(SUMMARIES_DIR / "all_analyses_index.json", 'w') as f:
            json.dump(all_analyses, f, indent=2, ensure_ascii=False)
        print(f"✓ Index: {len(all_analyses)} articles")


if __name__ == '__main__':
    asyncio.run(main())
