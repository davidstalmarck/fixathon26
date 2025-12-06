#!/usr/bin/env python3
"""
Process Articles with Multi-Stage Claude AI Pipeline
Uses multiple specialized prompts for high-quality extraction
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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


class MultiStageArticleProcessor:
    """Process articles using multiple specialized Claude prompts"""

    def __init__(self, api_key: str):
        """Initialize processor with Claude API key"""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def extract_pmid_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract PMID from filename

        Args:
            filename: XML filename (e.g., "PMC12345_PMID67890.xml")

        Returns:
            PMID string or None
        """
        match = re.search(r'PMID(\d+)', filename)
        if match:
            return match.group(1)
        return None

    def clean_xml_text(self, xml_path: Path) -> Dict[str, str]:
        """
        Extract and clean text sections from XML article

        Args:
            xml_path: Path to XML file

        Returns:
            Dictionary with title, abstract, and body text
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Extract title
            title_elem = root.find('.//article-title')
            title = ""
            if title_elem is not None:
                # Get all text including from nested elements
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

            return {
                'title': title,
                'abstract': abstract,
                'body': body
            }

        except Exception as e:
            print(f"  ✗ Error parsing XML: {e}")
            return {'title': '', 'abstract': '', 'body': ''}

    def stage1_clean_text(self, text_sections: Dict[str, str]) -> str:
        """
        Stage 1: Clean and prepare text using Claude
        Removes XML artifacts, fixes formatting, prepares for analysis

        Args:
            text_sections: Dictionary with title, abstract, body

        Returns:
            Cleaned text ready for analysis
        """
        combined_text = f"""Title: {text_sections['title']}

Abstract:
{text_sections['abstract']}

Full Text:
{text_sections['body']}"""

        # Truncate if too long
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
            print(f"    Stage 1: Cleaning text...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )
            cleaned_text = response.content[0].text
            print(f"    ✓ Text cleaned ({len(cleaned_text):,} chars)")
            return cleaned_text

        except Exception as e:
            print(f"    ✗ Stage 1 error: {e}")
            return combined_text

    def stage2_comprehensive_summary(self, cleaned_text: str, pmid: str) -> str:
        """
        Stage 2: Write comprehensive 1-2 page summary

        Args:
            cleaned_text: Cleaned article text
            pmid: PubMed ID

        Returns:
            Detailed summary
        """
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
            print(f"    Stage 2: Generating comprehensive summary...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.content[0].text
            print(f"    ✓ Summary generated ({len(summary):,} chars)")
            return summary

        except Exception as e:
            print(f"    ✗ Stage 2 error: {e}")
            return ""

    def stage3_extract_molecules(self, cleaned_text: str) -> List[str]:
        """
        Stage 3: Extract ALL molecules with specialized focus

        Args:
            cleaned_text: Cleaned article text

        Returns:
            List of molecules
        """
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
            print(f"    Stage 3: Extracting molecules...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON array
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                molecules = json.loads(json_match.group())
                print(f"    ✓ Found {len(molecules)} molecules")
                return molecules
            else:
                print(f"    ⚠️  Could not parse molecules list")
                return []

        except Exception as e:
            print(f"    ✗ Stage 3 error: {e}")
            return []

    def stage4_extract_topics_keywords(self, cleaned_text: str, pmid: str) -> Dict:
        """
        Stage 4: Extract topics and keywords

        Args:
            cleaned_text: Cleaned article text
            pmid: PubMed ID

        Returns:
            Dictionary with topics and keywords
        """
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
            print(f"    Stage 4: Extracting topics and keywords...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                print(f"    ✓ Found {len(result.get('topics', []))} topics, {len(result.get('keywords', []))} keywords")
                return result
            else:
                print(f"    ⚠️  Could not parse topics/keywords")
                return {"pmid": pmid, "topics": [], "keywords": []}

        except Exception as e:
            print(f"    ✗ Stage 4 error: {e}")
            return {"pmid": pmid, "topics": [], "keywords": []}

    def process_article(self, xml_path: Path) -> Optional[Dict]:
        """
        Process a single article through all stages

        Args:
            xml_path: Path to XML file

        Returns:
            Complete analysis results or None if already processed
        """
        # Extract PMID from filename
        pmid = self.extract_pmid_from_filename(xml_path.name)
        if not pmid:
            print(f"  ✗ Could not extract PMID from filename: {xml_path.name}")
            return None

        # Check if already processed
        output_file = SUMMARIES_DIR / f"PMID{pmid}_analysis.json"
        if output_file.exists():
            print(f"  ✓ Already processed, skipping")
            return None

        print(f"\nProcessing PMID {pmid}")
        print(f"  Source: {xml_path.name}")

        # Extract raw text from XML
        print(f"  Extracting text from XML...")
        text_sections = self.clean_xml_text(xml_path)

        if not text_sections['body'] or len(text_sections['body']) < 500:
            print(f"  ✗ Insufficient text extracted ({len(text_sections.get('body', ''))} chars)")
            return None

        print(f"  ✓ Extracted: Title={len(text_sections['title'])} chars, "
              f"Abstract={len(text_sections['abstract'])} chars, "
              f"Body={len(text_sections['body'])} chars")

        # Multi-stage processing
        print(f"\n  Running multi-stage analysis:")

        # Stage 1: Clean text
        cleaned_text = self.stage1_clean_text(text_sections)

        # Stage 2: Comprehensive summary
        comprehensive_summary = self.stage2_comprehensive_summary(cleaned_text, pmid)

        # Stage 3: Extract molecules
        molecules = self.stage3_extract_molecules(cleaned_text)

        # Stage 4: Topics and keywords
        topics_keywords = self.stage4_extract_topics_keywords(cleaned_text, pmid)

        # Compile results
        result = {
            'pmid': pmid,
            'xml_file': str(xml_path.name),
            'title': text_sections['title'],
            'abstract': text_sections['abstract'],
            'comprehensive_summary': comprehensive_summary,
            'topics': topics_keywords.get('topics', []),
            'keywords': topics_keywords.get('keywords', []),
            'molecules': molecules,
            'text_length': {
                'title': len(text_sections['title']),
                'abstract': len(text_sections['abstract']),
                'body': len(text_sections['body']),
                'cleaned': len(cleaned_text)
            }
        }

        # Save result
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n  ✓ Processing complete!")
        print(f"    Summary: {len(comprehensive_summary):,} chars")
        print(f"    Topics: {len(result['topics'])}")
        print(f"    Keywords: {len(result['keywords'])}")
        print(f"    Molecules: {len(molecules)}")
        print(f"    Saved to: {output_file.name}")

        return result


def main():
    """Main processing workflow"""
    print("="*80)
    print("Multi-Stage Article Processing Pipeline with Claude AI")
    print("="*80 + "\n")

    # Test Claude API connection
    print("Testing Claude API connection...")
    try:
        test_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        test_response = test_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with: OK"}]
        )
        print(f"✓ Claude API connected successfully")
        print(f"  Model: claude-sonnet-4-20250514\n")
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
    print("Processing pipeline:")
    print("  Stage 1: Clean and prepare text")
    print("  Stage 2: Generate comprehensive 1-2 page summary")
    print("  Stage 3: Extract ALL molecules (thorough scan)")
    print("  Stage 4: Extract topics and keywords")
    print()

    # Initialize processor
    processor = MultiStageArticleProcessor(api_key=CLAUDE_API_KEY)

    # Process each article
    results = []
    processed_count = 0
    skipped_count = 0
    error_count = 0

    for idx, xml_path in enumerate(xml_files, 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(xml_files)}]")

        try:
            result = processor.process_article(xml_path)

            if result is None:
                skipped_count += 1
            else:
                results.append(result)
                processed_count += 1

        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue

        # Save progress every 5 articles
        if idx % 5 == 0:
            progress_file = SUMMARIES_DIR / "processing_progress.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed': processed_count,
                    'skipped': skipped_count,
                    'errors': error_count,
                    'total': len(xml_files),
                    'last_processed': idx
                }, f, indent=2)
            print(f"\n  📊 Progress: {processed_count} processed, {skipped_count} skipped, {error_count} errors")

    # Final summary
    print("\n" + "="*80)
    print("Processing Summary")
    print("="*80)
    print(f"Total XML files: {len(xml_files)}")
    print(f"Newly processed: {processed_count}")
    print(f"Already processed (skipped): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"\nAnalysis files saved to: {SUMMARIES_DIR}/")
    print("="*80)

    # Create combined index
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
        print(f"✓ Created master index: {index_file}")
        print(f"  Total articles indexed: {len(all_analyses)}")


if __name__ == '__main__':
    main()
