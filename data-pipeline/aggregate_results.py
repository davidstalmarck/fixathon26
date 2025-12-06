#!/usr/bin/env python3
"""
Aggregate PubMed Results
Combine multiple result files into one, removing duplicates based on PMID
"""

import json
import csv
import glob
from pathlib import Path
from typing import List, Dict
from collections import OrderedDict


# Directory containing the result files
INPUT_DIR = Path("pubmed-ids-results")
OUTPUT_DIR = Path("pubmed-ids-results")


def load_json_files(pattern: str = "results_*.json") -> List[Dict]:
    """
    Load all JSON result files matching the pattern from the input directory

    Args:
        pattern: Glob pattern to match files (default: results_*.json)

    Returns:
        List of all articles from all files
    """
    all_articles = []
    search_pattern = str(INPUT_DIR / pattern)
    json_files = glob.glob(search_pattern)

    print(f"Found {len(json_files)} JSON files to aggregate in {INPUT_DIR}")

    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                all_articles.extend(articles)
                print(f"  ✓ Loaded {len(articles)} articles from {Path(json_file).name}")
        except Exception as e:
            print(f"  ✗ Error loading {json_file}: {e}")
            continue

    return all_articles


def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    Remove duplicate articles based on PMID
    Keeps the first occurrence of each PMID

    Args:
        articles: List of article dictionaries

    Returns:
        Deduplicated list of articles
    """
    seen_pmids = set()
    unique_articles = []
    duplicates_count = 0

    for article in articles:
        pmid = article.get('pmid', '')

        if pmid and pmid not in seen_pmids:
            seen_pmids.add(pmid)
            unique_articles.append(article)
        else:
            duplicates_count += 1

    print(f"\nDeduplication summary:")
    print(f"  Total articles loaded: {len(articles)}")
    print(f"  Unique articles: {len(unique_articles)}")
    print(f"  Duplicates removed: {duplicates_count}")

    return unique_articles


def save_aggregated_results(articles: List[Dict],
                            json_output: str = "aggregated_results.json",
                            csv_output: str = "aggregated_results.csv"):
    """
    Save aggregated articles to JSON and CSV in the output directory

    Args:
        articles: List of article dictionaries
        json_output: Output JSON filename
        csv_output: Output CSV filename
    """
    if not articles:
        print("No articles to save!")
        return

    # Create full paths in output directory
    json_path = OUTPUT_DIR / json_output
    csv_path = OUTPUT_DIR / csv_output

    # Save JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(articles)} articles to {json_path}")

    # Save CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=articles[0].keys())
        writer.writeheader()
        writer.writerows(articles)
    print(f"✓ Saved {len(articles)} articles to {csv_path}")


def main():
    """Main aggregation workflow"""
    print("="*80)
    print("PubMed Results Aggregation")
    print("="*80 + "\n")

    # Load all result files
    all_articles = load_json_files("results_*.json")

    if not all_articles:
        print("\nNo articles found. Make sure result files exist with pattern 'results_*.json'")
        return

    # Remove duplicates
    unique_articles = deduplicate_articles(all_articles)

    # Save aggregated results
    save_aggregated_results(unique_articles)

    print("\n" + "="*80)
    print("Aggregation completed!")
    print("="*80)


if __name__ == '__main__':
    main()