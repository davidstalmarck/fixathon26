#!/usr/bin/env python3
"""
Batch PubMed Scraper
Run multiple queries and save results for each
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pubmed_scraper import PubMedScraper
from datetime import datetime

# Load environment variables
load_dotenv()

# Create output directory
OUTPUT_DIR = Path("pubmed-ids-results")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    """Run multiple PubMed queries"""

    # Initialize scraper
    scraper = PubMedScraper(
        email=os.getenv('PUBMED_EMAIL'),
        api_key=os.getenv('PUBMED_API_KEY')
    )

    # Define your queries
    queries  = [
    # Category 1: Outcome-Based (no compound names)
    "methane reduction in the rumen using any compound, additive, or substrate",
    "studies showing reduced methane in vitro in rumen systems, excluding common inhibitors like 3-NOP, nitrate, fumarate, monensin, tannins, saponins, Asparagopsis, probiotics, yeast",
    "compounds or chemicals that inhibit methanogenesis in the rumen",
    "antimethanogenic compounds tested in the rumen, excluding papers focused on bacteria or microbes",

    # Category 2: Hydrogen fate / sinks (mechanism-based)
    "alternative hydrogen sinks in the rumen, excluding fumarate, nitrate, and sulfate",
    "hydrogen consumption pathways in the rumen",
    "how hydrogen is utilized in rumen or ruminal fermentation",
    "electron sink mechanisms in the rumen or anaerobic fermentation",
    "alternative electron acceptors in rumen fermentation",
    "hydrogen balance and where metabolic hydrogen goes in the rumen",
    "fate or redirection of metabolic hydrogen in the rumen",
    "reducing equivalents and hydrogen disposal in rumen fermentation",

    # Category 3: Older fermentation / artificial rumen literature
    "classic rumen fermentation modifier chemicals",
    "compounds or additives that stimulate, enhance, or alter ruminal fermentation",
    "in vitro rumen fermentation studies testing acids, substrates, or chemicals",
    "artificial rumen or continuous culture studies testing compounds or substrates",
    "RUSITEC studies evaluating additives, compounds, or treatments",
    "continuous culture rumen studies with treatments or alternative substrates",

    # Category 4: VFA manipulation / adjacent metabolism
    "ways to stimulate propionate production in the rumen without focusing on methane or probiotics",
    "ways to enhance butyrate production in the rumen without focusing on methane or probiotics",
    "compounds or additives that shift the rumen VFA ratio",
    "propionate precursors used in rumen fermentation",
    "succinate pathway activity or stimulation in the rumen",
    "acrylate pathway activity or stimulation in the rumen",
    "glucogenic precursors affecting rumen fermentation",

    # Category 5: Chemical classes (not specific named compounds)
    "dicarboxylic acids affecting rumen fermentation other than fumarate or malate",
    "hydroxy acids involved in rumen fermentation",
    "keto acids involved in rumen fermentation",
    "carboxylic acids that alter rumen fermentation or methane",
    "phenolic compounds affecting rumen fermentation but not tannins",
    "flavonoids that influence rumen fermentation (excluding reviews)",
    "terpenes that affect rumen fermentation or methane",
    "terpenoids studied in the rumen",
    "quinones studied in rumen fermentation",
    "medium-chain fatty acids with antimicrobial or methane effects in the rumen",
    "MCFAs studied in the rumen",
    "lauric acid effects in the rumen",
    "caprylic acid effects in the rumen",
    "capric acid effects in the rumen",
    "caproic acid effects in the rumen",
    "short-chain fatty acids used as rumen additives or supplements",
    "lipids affecting rumen methane (excluding reviews)",

    # Category 6: Screening / comparative studies
    "screening studies that test multiple compounds or molecules in rumen systems",
    "in vitro rumen screening experiments measuring methane",
    "comparative studies of multiple additives or compounds on rumen fermentation",
    "dose–response studies of rumen additives or compounds",
    "structure–activity relationship studies for antimethanogenic effects in the rumen",

    # Category 7: Reviews to mine reference lists
    "reviews on rumen methane mitigation or inhibitors",
    "systematic reviews on enteric methane reduction",
    "reviews on manipulating rumen fermentation",
    "reviews on rumen methanogenesis inhibitors or related chemicals",
]


    # Configuration
    max_results_per_query = 10000

    # Run each query
    for idx, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {idx}/{len(queries)}: {query}")
        print(f"{'='*80}\n")

        try:
            # Scrape articles
            articles = scraper.scrape(query, max_results=max_results_per_query)

            if articles:
                # Create safe filename from query
                safe_query = query.replace(' ', '_').replace('/', '_')[:50]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                # Save with query-specific filenames in the output directory
                json_filename = OUTPUT_DIR / f"results_{idx}_{safe_query}_{timestamp}.json"
                csv_filename = OUTPUT_DIR / f"results_{idx}_{safe_query}_{timestamp}.csv"

                scraper.save_to_json(articles, str(json_filename))
                scraper.save_to_csv(articles, str(csv_filename))

                print(f"\n✓ Completed query {idx}: {len(articles)} articles saved")
            else:
                print(f"\n✗ No results for query {idx}")

        except Exception as e:
            print(f"\n✗ Error processing query {idx}: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"Batch scraping completed! Processed {len(queries)} queries.")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
