#!/usr/bin/env python3
"""
Verify and Fix Summaries
Checks that molecules and keywords actually exist in the original XML
Removes items that don't exist, keeps the rest of the summary intact
"""

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

# Directories
XML_DIR = Path("pubmed-articles/xmls_all")
SUMMARIES_DIR = Path("pubmed-articles/summaries")


def extract_pmid_from_filename(filename: str) -> str:
    """Extract PMID from filename"""
    match = re.search(r'PMID(\d+)', filename)
    return match.group(1) if match else None


def read_xml_text(xml_path: Path) -> str:
    """Read all text content from XML"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Get all text from the entire XML
        all_text = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                all_text.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                all_text.append(elem.tail.strip())

        return ' '.join(all_text).lower()
    except Exception as e:
        print(f"  Error reading XML: {e}")
        return ""


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove special chars)"""
    # Convert to lowercase
    text = text.lower()

    # Replace Greek letters and special characters
    replacements = {
        'α': 'alpha',
        'β': 'beta',
        'γ': 'gamma',
        'δ': 'delta',
        'ε': 'epsilon',
        'κ': 'kappa',
        'λ': 'lambda',
        'μ': 'mu',
        'π': 'pi',
        'σ': 'sigma',
        'τ': 'tau',
        'ω': 'omega',
        '–': '-',
        '—': '-',
        ''': "'",
        ''': "'",
        '"': '"',
        '"': '"',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    return text


def check_term_exists(term: str, xml_text: str) -> bool:
    """Check if a term exists in the XML text"""
    if not term or not xml_text:
        return False

    # Normalize both
    term_norm = normalize_text(term)
    xml_norm = normalize_text(xml_text)

    # Try exact match first
    if term_norm in xml_norm:
        return True

    # Try without hyphens
    term_no_hyphen = term_norm.replace('-', ' ')
    if term_no_hyphen in xml_norm:
        return True

    # Try with hyphens removed from both
    term_compact = term_norm.replace('-', '')
    xml_compact = xml_norm.replace('-', '')
    if term_compact in xml_compact:
        return True

    # For multi-word terms, try partial matches
    if ' ' in term_norm or '-' in term_norm:
        words = re.split(r'[\s\-]+', term_norm)
        # All significant words must be present
        significant_words = [w for w in words if len(w) > 3]
        if significant_words:
            return all(word in xml_norm for word in significant_words)

    return False


def verify_molecules(molecules: list, xml_text: str) -> tuple:
    """Verify molecules exist in XML, return (verified, removed)"""
    verified = []
    removed = []

    for molecule in molecules:
        if check_term_exists(molecule, xml_text):
            verified.append(molecule)
        else:
            removed.append(molecule)

    return verified, removed


def verify_keywords(keywords: list, xml_text: str) -> tuple:
    """Verify keywords exist in XML, return (verified, removed)"""
    verified = []
    removed = []

    for keyword in keywords:
        if check_term_exists(keyword, xml_text):
            verified.append(keyword)
        else:
            removed.append(keyword)

    return verified, removed


def verify_summary(summary_path: Path, xml_path: Path, fix: bool = False) -> dict:
    """
    Verify a summary file against its XML source

    Args:
        summary_path: Path to summary JSON
        xml_path: Path to XML source
        fix: If True, update the summary file with corrections

    Returns:
        dict with verification results
    """
    try:
        # Read summary
        with open(summary_path, 'r') as f:
            summary = json.load(f)

        pmid = summary.get('pmid', 'unknown')

        # Read XML text
        xml_text = read_xml_text(xml_path)
        if not xml_text:
            return {
                'pmid': pmid,
                'error': 'Could not read XML',
                'fixed': False
            }

        # Get current data
        molecules = summary.get('molecules', [])
        keywords = summary.get('keywords', [])

        # Verify
        verified_molecules, removed_molecules = verify_molecules(molecules, xml_text)
        verified_keywords, removed_keywords = verify_keywords(keywords, xml_text)

        result = {
            'pmid': pmid,
            'molecules_before': len(molecules),
            'molecules_after': len(verified_molecules),
            'molecules_removed': removed_molecules,
            'keywords_before': len(keywords),
            'keywords_after': len(verified_keywords),
            'keywords_removed': removed_keywords,
            'fixed': False
        }

        # Fix if requested and there are changes
        if fix and (removed_molecules or removed_keywords):
            summary['molecules'] = verified_molecules
            summary['keywords'] = verified_keywords

            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            result['fixed'] = True

        return result

    except Exception as e:
        return {
            'pmid': extract_pmid_from_filename(summary_path.name),
            'error': str(e),
            'fixed': False
        }


def main(fix: bool = False):
    """
    Main verification function

    Args:
        fix: If True, actually update the summary files
    """
    print("="*80)
    if fix:
        print("VERIFYING AND FIXING SUMMARIES")
    else:
        print("VERIFYING SUMMARIES (DRY RUN)")
    print("="*80)

    summary_files = list(SUMMARIES_DIR.glob("PMID*_analysis.json"))
    print(f"\nFound {len(summary_files)} summary files to check\n")

    total_stats = {
        'checked': 0,
        'fixed': 0,
        'errors': 0,
        'molecules_removed': 0,
        'keywords_removed': 0,
    }

    issues = []

    for idx, summary_file in enumerate(summary_files, 1):
        pmid = extract_pmid_from_filename(summary_file.name)

        # Find corresponding XML
        xml_files = list(XML_DIR.glob(f"*PMID{pmid}.xml"))

        if not xml_files:
            print(f"[{idx}/{len(summary_files)}] ⚠️  PMID {pmid}: No XML found")
            total_stats['errors'] += 1
            continue

        xml_file = xml_files[0]

        # Verify
        result = verify_summary(summary_file, xml_file, fix=fix)
        total_stats['checked'] += 1

        if 'error' in result:
            print(f"[{idx}/{len(summary_files)}] ❌ PMID {pmid}: {result['error']}")
            total_stats['errors'] += 1
            continue

        # Check for issues
        mol_removed = len(result['molecules_removed'])
        kw_removed = len(result['keywords_removed'])

        if mol_removed > 0 or kw_removed > 0:
            total_stats['molecules_removed'] += mol_removed
            total_stats['keywords_removed'] += kw_removed

            if result['fixed']:
                total_stats['fixed'] += 1

            status = "✓ FIXED" if result['fixed'] else "⚠️  ISSUES"
            print(f"[{idx}/{len(summary_files)}] {status} PMID {pmid}:")

            if mol_removed > 0:
                print(f"    Molecules: {result['molecules_before']} → {result['molecules_after']} (-{mol_removed})")
                if mol_removed <= 5:
                    print(f"      Removed: {', '.join(result['molecules_removed'])}")
                else:
                    print(f"      Removed: {', '.join(result['molecules_removed'][:5])}... (+{mol_removed-5} more)")

            if kw_removed > 0:
                print(f"    Keywords: {result['keywords_before']} → {result['keywords_after']} (-{kw_removed})")
                if kw_removed <= 5:
                    print(f"      Removed: {', '.join(result['keywords_removed'])}")
                else:
                    print(f"      Removed: {', '.join(result['keywords_removed'][:5])}... (+{kw_removed-5} more)")

            issues.append(result)
        else:
            if idx % 10 == 0:  # Show progress every 10 files
                print(f"[{idx}/{len(summary_files)}] ✓ PMID {pmid}: All verified")

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print(f"\nChecked: {total_stats['checked']} summaries")
    print(f"Issues found: {len(issues)} summaries")
    print(f"Fixed: {total_stats['fixed']} summaries")
    print(f"Errors: {total_stats['errors']}")
    print(f"\nTotal molecules removed: {total_stats['molecules_removed']}")
    print(f"Total keywords removed: {total_stats['keywords_removed']}")

    if not fix and issues:
        print("\n" + "="*80)
        print("TO FIX THE ISSUES:")
        print("="*80)
        print("Run with --fix flag to update the summary files:")
        print("  uv run python data-pipeline/verify_and_fix_summaries.py --fix")


if __name__ == '__main__':
    import sys

    # Check for --fix flag
    fix_mode = '--fix' in sys.argv

    if not fix_mode:
        print("\n⚠️  DRY RUN MODE - No files will be modified")
        print("Add --fix flag to actually update the files\n")

    main(fix=fix_mode)
