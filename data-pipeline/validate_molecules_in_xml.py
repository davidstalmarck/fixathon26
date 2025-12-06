#!/usr/bin/env python3
"""
Validate molecules by checking if they actually appear in the original XML files.
Handles special characters like Greek/Latin letters in &#111; format.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Set
import html


# Directories
SUMMARIES_DIR = Path("pubmed-articles/summaries")
XML_DIR = Path("pubmed-articles/xmls")


def normalize_text(text: str) -> str:
    """
    Normalize text by:
    - Converting HTML entities (&#111; -> actual character)
    - Lowercasing
    - Removing extra whitespace
    """
    # Unescape HTML entities
    text = html.unescape(text)
    # Lowercase
    text = text.lower()
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def extract_text_from_xml(xml_file: Path) -> str:
    """Extract all text content from XML file"""
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"    Error reading {xml_file}: {e}")
        return ""


def find_molecule_in_text(molecule: str, text: str) -> bool:
    """
    Check if molecule name appears in text.
    Handles variations and special characters.
    """
    # Normalize both
    normalized_molecule = normalize_text(molecule)
    normalized_text = normalize_text(text)

    # Simple substring check
    if normalized_molecule in normalized_text:
        return True

    # Check for word boundaries (more strict)
    pattern = r'\b' + re.escape(normalized_molecule) + r'\b'
    if re.search(pattern, normalized_text):
        return True

    # Check without spaces (e.g., "alpha-ketoglutarate" vs "alpha ketoglutarate")
    no_space_molecule = normalized_molecule.replace(' ', '').replace('-', '')
    no_space_text = normalized_text.replace(' ', '').replace('-', '')
    if len(no_space_molecule) > 3 and no_space_molecule in no_space_text:
        return True

    return False


def validate_molecules_in_xml(article_file: Path, fix: bool = False) -> Dict:
    """Validate that molecules appear in the corresponding XML file"""

    try:
        # Read summary JSON
        with open(article_file, 'r', encoding='utf-8') as f:
            article_data = json.load(f)

        pmid = article_data.get('pmid', 'unknown')
        molecules = article_data.get('molecules', [])

        if not molecules:
            print(f"PMID {pmid}: No molecules to validate")
            return None

        print(f"\nPMID {pmid}: Validating {len(molecules)} molecules in XML...")

        # Find corresponding XML file
        xml_files = list(XML_DIR.glob(f"*_PMID{pmid}.xml"))

        if not xml_files:
            print(f"  ⚠️  No XML file found for PMID {pmid}")
            return {
                'valid': [],
                'invalid': molecules,
                'not_found': molecules,
                'no_xml': True
            }

        xml_file = xml_files[0]
        print(f"  Using XML: {xml_file.name}")

        # Extract XML content
        xml_text = extract_text_from_xml(xml_file)

        # Validate each molecule
        valid_molecules = []
        invalid_molecules = []

        for molecule in molecules:
            if find_molecule_in_text(molecule, xml_text):
                valid_molecules.append(molecule)
            else:
                invalid_molecules.append(molecule)

        # Print results
        print(f"  ✓ Found in XML: {len(valid_molecules)}")
        print(f"  ✗ NOT found in XML: {len(invalid_molecules)}")

        if invalid_molecules:
            print(f"  Missing molecules: {', '.join(invalid_molecules[:5])}")
            if len(invalid_molecules) > 5:
                print(f"    ... and {len(invalid_molecules) - 5} more")

        # Update file if fix flag is set
        if fix and invalid_molecules:
            article_data['molecules'] = valid_molecules
            article_data['molecules_validation'] = {
                'method': 'xml_verification',
                'total_original': len(molecules),
                'found_in_xml': len(valid_molecules),
                'not_found_in_xml': len(invalid_molecules),
                'removed_molecules': invalid_molecules
            }

            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, indent=2, ensure_ascii=False)

            print(f"  💾 Updated file - kept {len(valid_molecules)} molecules found in XML")

        return {
            'valid': valid_molecules,
            'invalid': invalid_molecules,
            'not_found': invalid_molecules,
            'no_xml': False
        }

    except Exception as e:
        print(f"Error processing {article_file}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main validation routine"""

    import argparse
    parser = argparse.ArgumentParser(
        description='Validate molecules by checking if they appear in original XML files'
    )
    parser.add_argument('--fix', action='store_true',
                       help='Fix files by removing molecules not found in XML')
    parser.add_argument('--pmid', type=str,
                       help='Validate specific PMID only')
    parser.add_argument('--limit', type=int,
                       help='Limit number of articles to process')
    args = parser.parse_args()

    print("="*80)
    print("Molecule Validation - XML Verification")
    print("Checking if molecules actually appear in original XML files")
    print("="*80 + "\n")

    # Get article files
    if args.pmid:
        article_files = [SUMMARIES_DIR / f"PMID{args.pmid}_analysis.json"]
    else:
        article_files = sorted(SUMMARIES_DIR.glob("PMID*_analysis.json"))

    if args.limit:
        article_files = article_files[:args.limit]

    print(f"Found {len(article_files)} article(s) to validate")
    if args.fix:
        print("⚠️  FIX MODE: Will remove molecules not found in XML\n")
    else:
        print("DRY RUN: Use --fix to update files\n")

    # Process each article
    all_results = []
    no_xml_count = 0

    for article_file in article_files:
        result = validate_molecules_in_xml(article_file, fix=args.fix)
        if result:
            all_results.append(result)
            if result.get('no_xml'):
                no_xml_count += 1

    # Overall summary
    print("\n" + "="*80)
    print("Validation Summary")
    print("="*80)

    total_valid = sum(len(r['valid']) for r in all_results)
    total_invalid = sum(len(r['invalid']) for r in all_results)

    print(f"Articles processed: {len(all_results)}")
    print(f"Articles without XML: {no_xml_count}")
    print(f"Total molecules found in XML: {total_valid}")
    print(f"Total molecules NOT found in XML: {total_invalid}")

    if total_valid + total_invalid > 0:
        percentage = (total_valid / (total_valid + total_invalid)) * 100
        print(f"Success rate: {percentage:.1f}%")

    # Most common missing molecules
    if all_results:
        from collections import defaultdict
        missing_counts = defaultdict(int)
        for result in all_results:
            for missing in result['not_found']:
                missing_counts[missing] += 1

        if missing_counts:
            print("\nMost common molecules NOT found in XML:")
            for molecule, count in sorted(missing_counts.items(),
                                        key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {count}x: {molecule}")

    print("="*80)


if __name__ == '__main__':
    main()