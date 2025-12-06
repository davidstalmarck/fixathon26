#!/usr/bin/env python3
"""
Check Already Processed Files
Analyzes what's been downloaded and processed, identifies gaps and issues
"""

import json
from pathlib import Path
from collections import defaultdict

# Directories
XML_DIR = Path("pubmed-articles/xmls")
XML_ALL_DIR = Path("pubmed-articles/xmls_all")
PDF_DIR = Path("pubmed-articles/pdfs")
SUMMARIES_DIR = Path("pubmed-articles/summaries")
IDS_DIR = Path("pubmed-ids-results")


def extract_pmid(filename: str) -> str:
    """Extract PMID from filename"""
    import re
    match = re.search(r'PMID(\d+)', filename)
    return match.group(1) if match else None


def check_summaries():
    """Check processed summaries for issues"""
    print("\n" + "="*80)
    print("SUMMARIES ANALYSIS")
    print("="*80)

    summary_files = list(SUMMARIES_DIR.glob("PMID*_analysis.json"))
    print(f"\nTotal summary files: {len(summary_files)}")

    issues = {
        'empty_summary': [],
        'no_molecules': [],
        'few_molecules': [],  # < 10
        'no_keywords': [],
        'no_topics': [],
        'short_summary': [],  # < 1000 chars
    }

    stats = {
        'total_molecules': 0,
        'total_keywords': 0,
        'total_topics': 0,
        'total_summary_length': 0,
    }

    for summary_file in summary_files:
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)

            pmid = data.get('pmid', 'unknown')
            summary = data.get('comprehensive_summary', '')
            molecules = data.get('molecules', [])
            keywords = data.get('keywords', [])
            topics = data.get('topics', [])

            # Track issues
            if not summary or len(summary) == 0:
                issues['empty_summary'].append(pmid)
            elif len(summary) < 1000:
                issues['short_summary'].append((pmid, len(summary)))

            if not molecules:
                issues['no_molecules'].append(pmid)
            elif len(molecules) < 10:
                issues['few_molecules'].append((pmid, len(molecules)))

            if not keywords:
                issues['no_keywords'].append(pmid)

            if not topics:
                issues['no_topics'].append(pmid)

            # Collect stats
            stats['total_molecules'] += len(molecules)
            stats['total_keywords'] += len(keywords)
            stats['total_topics'] += len(topics)
            stats['total_summary_length'] += len(summary)

        except Exception as e:
            print(f"  Error reading {summary_file.name}: {e}")

    # Print stats
    print("\n--- Summary Statistics ---")
    if len(summary_files) > 0:
        print(f"Average molecules per article: {stats['total_molecules'] / len(summary_files):.1f}")
        print(f"Average keywords per article: {stats['total_keywords'] / len(summary_files):.1f}")
        print(f"Average topics per article: {stats['total_topics'] / len(summary_files):.1f}")
        print(f"Average summary length: {stats['total_summary_length'] / len(summary_files):.0f} chars")

    # Print issues
    print("\n--- Issues Found ---")
    print(f"Empty summaries: {len(issues['empty_summary'])}")
    if issues['empty_summary'][:5]:
        print(f"  Examples: {', '.join(issues['empty_summary'][:5])}")

    print(f"Short summaries (<1000 chars): {len(issues['short_summary'])}")
    if issues['short_summary'][:5]:
        print(f"  Examples: {', '.join([f'{pmid}({length})' for pmid, length in issues['short_summary'][:5]])}")

    print(f"No molecules: {len(issues['no_molecules'])}")
    if issues['no_molecules'][:5]:
        print(f"  Examples: {', '.join(issues['no_molecules'][:5])}")

    print(f"Few molecules (<10): {len(issues['few_molecules'])}")
    if issues['few_molecules'][:5]:
        print(f"  Examples: {', '.join([f'{pmid}({count})' for pmid, count in issues['few_molecules'][:5]])}")

    print(f"No keywords: {len(issues['no_keywords'])}")
    print(f"No topics: {len(issues['no_topics'])}")

    return issues, stats


def check_downloads():
    """Check downloaded files"""
    print("\n" + "="*80)
    print("DOWNLOADS ANALYSIS")
    print("="*80)

    xmls = list(XML_DIR.glob("*.xml")) if XML_DIR.exists() else []
    xmls_all = list(XML_ALL_DIR.glob("*.xml")) if XML_ALL_DIR.exists() else []
    pdfs = list(PDF_DIR.glob("*.pdf")) if PDF_DIR.exists() else []

    print(f"\nXMLs in xmls/: {len(xmls)}")
    print(f"XMLs in xmls_all/: {len(xmls_all)}")
    print(f"PDFs: {len(pdfs)}")

    # Extract PMIDs
    xml_pmids = set()
    for xml_file in xmls_all:
        pmid = extract_pmid(xml_file.name)
        if pmid:
            xml_pmids.add(pmid)

    pdf_pmids = set()
    for pdf_file in pdfs:
        pmid = extract_pmid(pdf_file.name)
        if pmid:
            pdf_pmids.add(pmid)

    print(f"\nUnique PMIDs with XMLs: {len(xml_pmids)}")
    print(f"Unique PMIDs with PDFs: {len(pdf_pmids)}")
    print(f"PMIDs with both PDF and XML: {len(xml_pmids & pdf_pmids)}")

    return xml_pmids, pdf_pmids


def check_progress():
    """Check overall progress"""
    print("\n" + "="*80)
    print("OVERALL PROGRESS")
    print("="*80)

    # Get total articles from aggregated results
    aggregated_file = IDS_DIR / "aggregated_results.json"
    total_articles = 0
    if aggregated_file.exists():
        with open(aggregated_file, 'r') as f:
            data = json.load(f)
            total_articles = len(data)

    # Get processed summaries
    summaries = list(SUMMARIES_DIR.glob("PMID*_analysis.json"))
    processed_pmids = set()
    for summary_file in summaries:
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
                pmid = data.get('pmid')
                if pmid:
                    processed_pmids.add(pmid)
        except:
            pass

    # Get downloaded XMLs
    xmls_all = list(XML_ALL_DIR.glob("*.xml")) if XML_ALL_DIR.exists() else []
    xml_pmids = set()
    for xml_file in xmls_all:
        pmid = extract_pmid(xml_file.name)
        if pmid:
            xml_pmids.add(pmid)

    print(f"\nTotal articles found (from PubMed): {total_articles:,}")
    print(f"Downloaded XMLs: {len(xml_pmids):,}")
    print(f"Processed summaries: {len(processed_pmids):,}")

    if len(xml_pmids) > 0:
        print(f"\nDownload progress: {len(xml_pmids)/total_articles*100:.1f}%")
        print(f"Processing progress (of downloaded): {len(processed_pmids)/len(xml_pmids)*100:.1f}%")
        print(f"Processing progress (of total): {len(processed_pmids)/total_articles*100:.1f}%")

    print(f"\nRemaining to download: {total_articles - len(xml_pmids):,}")
    print(f"Remaining to process: {len(xml_pmids) - len(processed_pmids):,}")

    # Find XMLs not yet processed
    unprocessed = xml_pmids - processed_pmids
    print(f"\nXMLs downloaded but not processed: {len(unprocessed):,}")
    if unprocessed and len(unprocessed) <= 10:
        print(f"  PMIDs: {', '.join(sorted(unprocessed))}")

    return {
        'total_articles': total_articles,
        'downloaded': len(xml_pmids),
        'processed': len(processed_pmids),
        'unprocessed': len(unprocessed),
    }


def generate_cleanup_script(issues):
    """Generate script to delete bad summaries"""
    print("\n" + "="*80)
    print("CLEANUP SCRIPT")
    print("="*80)

    bad_pmids = set()
    bad_pmids.update(issues['empty_summary'])
    bad_pmids.update([pmid for pmid, _ in issues['short_summary']])

    if bad_pmids:
        script_path = Path("data-pipeline/cleanup_bad_summaries.sh")
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# Delete summaries with issues\n\n")
            f.write(f"echo 'Deleting {len(bad_pmids)} bad summaries...'\n\n")

            for pmid in sorted(bad_pmids):
                f.write(f"rm -f pubmed-articles/summaries/PMID{pmid}_analysis.json\n")

            f.write("\necho 'Done! Run process_articles_fast.py to reprocess.'\n")

        script_path.chmod(0o755)
        print(f"\n✓ Created cleanup script: {script_path}")
        print(f"  Will delete {len(bad_pmids)} bad summaries")
        print(f"\nTo use: bash {script_path}")
    else:
        print("\n✓ No bad summaries found - nothing to clean up!")


def main():
    """Main check function"""
    print("="*80)
    print("CHECKING PROCESSED FILES")
    print("="*80)

    # Check downloads
    xml_pmids, pdf_pmids = check_downloads()

    # Check summaries
    issues, stats = check_summaries()

    # Check overall progress
    progress = check_progress()

    # Generate cleanup script if needed
    generate_cleanup_script(issues)

    print("\n" + "="*80)
    print("CHECK COMPLETE")
    print("="*80)
    print("\nNext steps:")
    if issues['empty_summary'] or issues['short_summary']:
        print("  1. Run: bash data-pipeline/cleanup_bad_summaries.sh")
        print("  2. Run: uv run python data-pipeline/process_articles_fast.py")
    else:
        print("  Run: uv run python data-pipeline/process_articles_fast.py")


if __name__ == '__main__':
    main()
