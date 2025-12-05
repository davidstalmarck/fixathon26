#!/usr/bin/env python3
"""
Download Full-Text Articles from PubMed
Attempts to fetch PDFs from PMC and other sources
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from xml.etree import ElementTree as ET

# Load environment variables
load_dotenv()

# Directories
INPUT_DIR = Path("pubmed-ids-results")
OUTPUT_DIR = Path("pubmed-articles")
PDF_DIR = OUTPUT_DIR / "pdfs"
XML_DIR = OUTPUT_DIR / "xmls"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)
XML_DIR.mkdir(exist_ok=True)

# NCBI E-utilities endpoints
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Rate limiting
RATE_DELAY = 0.34  # 3 requests per second without API key
if os.getenv('PUBMED_API_KEY'):
    RATE_DELAY = 0.1  # 10 requests per second with API key


class ArticleDownloader:
    """Downloads full-text articles from PubMed/PMC"""

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize downloader with credentials"""
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PubMedScraper/1.0 (Python; Academic Research)'
        })

    def get_pmc_id(self, pmid: str) -> Optional[str]:
        """
        Get PMC ID from PMID using ELink

        Args:
            pmid: PubMed ID

        Returns:
            PMC ID if available, None otherwise
        """
        params = {
            'dbfrom': 'pubmed',
            'db': 'pmc',
            'id': pmid,
            'retmode': 'xml'
        }

        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key

        try:
            time.sleep(RATE_DELAY)
            response = self.session.get(ELINK_URL, params=params)
            response.raise_for_status()

            root = ET.fromstring(response.text)
            pmc_id = root.find('.//Link/Id')

            if pmc_id is not None:
                return pmc_id.text

        except Exception as e:
            print(f"  Error getting PMC ID for PMID {pmid}: {e}")

        return None

    def download_pmc_pdf(self, pmcid: str, output_path: Path) -> bool:
        """
        Download PDF from PMC

        Args:
            pmcid: PMC ID (without PMC prefix)
            output_path: Where to save the PDF

        Returns:
            True if successful, False otherwise
        """
        # PMC OA PDF URL format
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/"

        try:
            time.sleep(RATE_DELAY)
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()

            # Check if we got a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                output_path.write_bytes(response.content)
                return True
            else:
                return False

        except Exception as e:
            print(f"  Error downloading PDF from PMC{pmcid}: {e}")
            return False

    def download_pmc_fulltext_xml(self, pmcid: str, output_path: Path) -> bool:
        """
        Download full-text XML from PMC using EFetch

        Args:
            pmcid: PMC ID (without PMC prefix)
            output_path: Where to save the XML

        Returns:
            True if successful, False otherwise
        """
        params = {
            'db': 'pmc',
            'id': pmcid,
            'rettype': 'full',
            'retmode': 'xml'
        }

        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key

        try:
            time.sleep(RATE_DELAY)
            response = self.session.get(EFETCH_URL, params=params)
            response.raise_for_status()

            output_path.write_text(response.text, encoding='utf-8')
            return True

        except Exception as e:
            print(f"  Error downloading XML from PMC{pmcid}: {e}")
            return False

    def try_download_article(self, article: Dict) -> Dict:
        """
        Attempt to download article in multiple formats

        Args:
            article: Article dictionary with metadata

        Returns:
            Dictionary with download status
        """
        pmid = article.get('pmid', '')
        title = article.get('title') or 'Unknown'
        title = title[:80] if title else 'Unknown'

        result = {
            'pmid': pmid,
            'title': title,
            'pdf_downloaded': False,
            'xml_downloaded': False,
            'pdf_path': None,
            'xml_path': None,
            'pmc_id': None
        }

        if not pmid:
            result['error'] = 'No PMID'
            return result

        print(f"\nProcessing PMID: {pmid}")
        print(f"  Title: {title}...")

        # Get PMC ID
        pmc_id = self.get_pmc_id(pmid)
        result['pmc_id'] = pmc_id

        if not pmc_id:
            print(f"  ✗ No PMC ID found (article may not be open access)")
            result['error'] = 'No PMC ID (not open access)'
            return result

        print(f"  ✓ Found PMC ID: PMC{pmc_id}")

        # Create output paths in separate folders
        pdf_path = PDF_DIR / f"PMC{pmc_id}_PMID{pmid}.pdf"
        xml_path = XML_DIR / f"PMC{pmc_id}_PMID{pmid}.xml"

        # Check if already downloaded
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            print(f"  ✓ PDF already exists, skipping")
            result['pdf_downloaded'] = True
            result['pdf_path'] = str(pdf_path)
            return result

        if xml_path.exists() and xml_path.stat().st_size > 1000:
            print(f"  ✓ XML already exists, skipping")
            result['xml_downloaded'] = True
            result['xml_path'] = str(xml_path)
            return result

        # Try to download PDF
        print(f"  Attempting PDF download...")
        if self.download_pmc_pdf(pmc_id, pdf_path):
            print(f"  ✓ PDF downloaded successfully")
            result['pdf_downloaded'] = True
            result['pdf_path'] = str(pdf_path)
        else:
            print(f"  ✗ PDF not available")

            # Try XML as fallback
            print(f"  Attempting XML download...")
            if self.download_pmc_fulltext_xml(pmc_id, xml_path):
                print(f"  ✓ XML downloaded successfully")
                result['xml_downloaded'] = True
                result['xml_path'] = str(xml_path)
            else:
                print(f"  ✗ XML not available")
                result['error'] = 'No full-text available'

        return result


def load_articles_from_json(json_file: Path) -> List[Dict]:
    """Load articles from a JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return []


def main():
    """Main download workflow"""
    print("="*80)
    print("PubMed Article Downloader")
    print("="*80 + "\n")

    # Initialize downloader
    downloader = ArticleDownloader(
        email=os.getenv('PUBMED_EMAIL'),
        api_key=os.getenv('PUBMED_API_KEY')
    )

    # Load aggregated results
    aggregated_file = INPUT_DIR / "aggregated_results1945.json"

    if not aggregated_file.exists():
        print(f"Error: {aggregated_file} not found!")
        print("Please run aggregate_results.py first.")
        return

    print(f"Loading articles from {aggregated_file}...")
    articles = load_articles_from_json(aggregated_file)
    print(f"Found {len(articles)} articles to process\n")

    # Download articles
    results = []
    success_count = 0
    no_pmc_count = 0
    error_count = 0

    for idx, article in enumerate(articles, 1):
        print(f"\n[{idx}/{len(articles)}]", end=" ")

        result = downloader.try_download_article(article)
        results.append(result)

        if result.get('pdf_downloaded') or result.get('xml_downloaded'):
            success_count += 1
        elif 'No PMC ID' in result.get('error', ''):
            no_pmc_count += 1
        else:
            error_count += 1

        # Save progress periodically
        if idx % 100 == 0:
            progress_file = OUTPUT_DIR / "download_progress.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"\n  Progress saved ({success_count} successful so far)")

    # Save final results
    final_results_file = OUTPUT_DIR / "download_results.json"
    with open(final_results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    # Summary
    print("\n" + "="*80)
    print("Download Summary")
    print("="*80)
    print(f"Total articles processed: {len(articles)}")
    print(f"Successfully downloaded: {success_count}")
    print(f"  - PDFs: {sum(1 for r in results if r.get('pdf_downloaded'))}")
    print(f"  - XMLs: {sum(1 for r in results if r.get('xml_downloaded'))}")
    print(f"Not open access (no PMC ID): {no_pmc_count}")
    print(f"Other errors: {error_count}")
    print(f"\nResults saved to: {final_results_file}")
    print(f"PDFs saved to: {PDF_DIR}/")
    print(f"XMLs saved to: {XML_DIR}/")
    print("="*80)


if __name__ == '__main__':
    main()