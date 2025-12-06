#!/usr/bin/env python3
"""Test processing a single article"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from process_articles_parallel import ParallelArticleProcessor
import os
from dotenv import load_dotenv

load_dotenv()

async def test_one():
    xml_file = Path("pubmed-articles/xmls/PMC10000110_PMID36899745.xml")

    if not xml_file.exists():
        print(f"File not found: {xml_file}")
        return

    print(f"Testing with: {xml_file.name}\n")

    processor = ParallelArticleProcessor(api_key=os.getenv('CLAUDE_API_KEY'))

    try:
        result = await processor.process_article(xml_file, 1, 1)

        if result:
            print("\n✓ Success!")
            print(f"PMID: {result['pmid']}")
            print(f"Summary length: {len(result.get('comprehensive_summary', ''))}")
            print(f"Molecules: {len(result.get('molecules', []))}")
        else:
            print("\n⚠️ Article already processed or skipped")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_one())
