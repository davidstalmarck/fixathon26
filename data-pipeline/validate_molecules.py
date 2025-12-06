#!/usr/bin/env python3
"""
Validate and fix molecule names in processed articles.
Checks if molecules actually exist using PubChem API and standardizes names.
"""

import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict


# Directories
SUMMARIES_DIR = Path("pubmed-articles/summaries")

# PubChem API settings
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
REQUEST_DELAY = 0.2  # Seconds between requests to avoid rate limiting


class MoleculeValidator:
    """Validate molecules using PubChem API"""

    def __init__(self):
        """Initialize validator with cache"""
        self.cache = {}  # Cache results to avoid repeated API calls
        self.session = requests.Session()

    def search_pubchem(self, molecule_name: str) -> Optional[Dict]:
        """Search PubChem for a molecule by name"""

        # Check cache first
        if molecule_name.lower() in self.cache:
            return self.cache[molecule_name.lower()]

        try:
            # Search by name
            url = f"{PUBCHEM_BASE_URL}/compound/name/{molecule_name}/JSON"
            response = self.session.get(url, timeout=10)

            time.sleep(REQUEST_DELAY)  # Rate limiting

            if response.status_code == 200:
                data = response.json()
                result = {
                    'found': True,
                    'cid': data['PC_Compounds'][0]['id']['id']['cid'],
                    'iupac_name': None,
                    'molecular_formula': None
                }

                # Try to get IUPAC name and formula
                try:
                    props = data['PC_Compounds'][0]['props']
                    for prop in props:
                        if prop['urn']['label'] == 'IUPAC Name' and prop['urn']['name'] == 'Preferred':
                            result['iupac_name'] = prop['value']['sval']
                        elif prop['urn']['label'] == 'Molecular Formula':
                            result['molecular_formula'] = prop['value']['sval']
                except:
                    pass

                self.cache[molecule_name.lower()] = result
                return result

            elif response.status_code == 404:
                # Not found
                self.cache[molecule_name.lower()] = {'found': False}
                return {'found': False}

            else:
                print(f"    ⚠️  API error for '{molecule_name}': {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Request error for '{molecule_name}': {e}")
            return None

    def validate_molecule(self, molecule_name: str) -> Dict:
        """Validate a single molecule and return standardized info"""

        result = self.search_pubchem(molecule_name)

        if result is None:
            return {
                'original_name': molecule_name,
                'valid': None,  # Unknown (API error)
                'standardized_name': molecule_name
            }

        if result['found']:
            # Use IUPAC name if available, otherwise keep original
            standardized = result.get('iupac_name') or molecule_name
            return {
                'original_name': molecule_name,
                'valid': True,
                'standardized_name': standardized,
                'cid': result['cid'],
                'molecular_formula': result.get('molecular_formula')
            }
        else:
            return {
                'original_name': molecule_name,
                'valid': False,
                'standardized_name': molecule_name
            }

    def validate_molecules_list(self, molecules: List[str]) -> Dict:
        """Validate a list of molecules"""

        results = {
            'valid': [],
            'invalid': [],
            'unknown': [],
            'details': []
        }

        for molecule in molecules:
            validation = self.validate_molecule(molecule)
            results['details'].append(validation)

            if validation['valid'] is True:
                results['valid'].append(validation['standardized_name'])
            elif validation['valid'] is False:
                results['invalid'].append(validation['original_name'])
            else:
                results['unknown'].append(validation['original_name'])

        return results


def validate_article_molecules(article_file: Path, validator: MoleculeValidator, fix: bool = False):
    """Validate molecules in a single article file"""

    try:
        with open(article_file, 'r', encoding='utf-8') as f:
            article_data = json.load(f)

        pmid = article_data.get('pmid', 'unknown')
        molecules = article_data.get('molecules', [])

        if not molecules:
            print(f"PMID {pmid}: No molecules to validate")
            return None

        print(f"\nPMID {pmid}: Validating {len(molecules)} molecules...")

        # Validate all molecules
        validation_results = validator.validate_molecules_list(molecules)

        # Print summary
        print(f"  ✓ Valid: {len(validation_results['valid'])}")
        print(f"  ✗ Invalid: {len(validation_results['invalid'])}")
        print(f"  ? Unknown: {len(validation_results['unknown'])}")

        if validation_results['invalid']:
            print(f"  Invalid molecules: {', '.join(validation_results['invalid'][:5])}")

        # Update file if fix flag is set
        if fix:
            article_data['molecules'] = validation_results['valid']
            article_data['molecules_validation'] = {
                'total_original': len(molecules),
                'valid': len(validation_results['valid']),
                'invalid': len(validation_results['invalid']),
                'unknown': len(validation_results['unknown']),
                'invalid_list': validation_results['invalid'],
                'details': validation_results['details']
            }

            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, indent=2, ensure_ascii=False)

            print(f"  💾 Updated file with {len(validation_results['valid'])} valid molecules")

        return validation_results

    except Exception as e:
        print(f"Error processing {article_file}: {e}")
        return None


def main():
    """Main validation routine"""

    import argparse
    parser = argparse.ArgumentParser(description='Validate molecules in processed articles')
    parser.add_argument('--fix', action='store_true', help='Fix files by removing invalid molecules')
    parser.add_argument('--pmid', type=str, help='Validate specific PMID only')
    parser.add_argument('--limit', type=int, help='Limit number of articles to process')
    args = parser.parse_args()

    print("="*80)
    print("Molecule Validation using PubChem API")
    print("="*80 + "\n")

    # Initialize validator
    validator = MoleculeValidator()

    # Get article files
    if args.pmid:
        article_files = [SUMMARIES_DIR / f"PMID{args.pmid}_analysis.json"]
    else:
        article_files = list(SUMMARIES_DIR.glob("PMID*_analysis.json"))

    if args.limit:
        article_files = article_files[:args.limit]

    print(f"Found {len(article_files)} article(s) to validate")
    if args.fix:
        print("⚠️  FIX MODE: Will update files with valid molecules only\n")
    else:
        print("DRY RUN: Use --fix to update files\n")

    # Process each article
    all_results = []
    for article_file in article_files:
        result = validate_article_molecules(article_file, validator, fix=args.fix)
        if result:
            all_results.append(result)

    # Overall summary
    print("\n" + "="*80)
    print("Validation Summary")
    print("="*80)

    total_valid = sum(len(r['valid']) for r in all_results)
    total_invalid = sum(len(r['invalid']) for r in all_results)
    total_unknown = sum(len(r['unknown']) for r in all_results)

    print(f"Articles processed: {len(all_results)}")
    print(f"Total valid molecules: {total_valid}")
    print(f"Total invalid molecules: {total_invalid}")
    print(f"Total unknown (API errors): {total_unknown}")

    # Most common invalid molecules
    if all_results:
        invalid_counts = defaultdict(int)
        for result in all_results:
            for invalid in result['invalid']:
                invalid_counts[invalid] += 1

        if invalid_counts:
            print("\nMost common invalid molecules:")
            for molecule, count in sorted(invalid_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {count}x: {molecule}")

    print("="*80)


if __name__ == '__main__':
    main()