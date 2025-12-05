# PubMed Scraper

A Python tool for scraping article metadata from PubMed using the NCBI E-utilities API.

## Features

- Search PubMed articles by keywords
- Fetch detailed metadata (title, authors, abstract, DOI, MeSH terms, etc.)
- Export results to JSON or CSV
- Respects NCBI rate limits
- Support for API keys for higher rate limits
- Environment variable configuration via .env

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Or if you don't have uv installed yet:
pip install uv
uv sync
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your credentials:
```
PUBMED_EMAIL=your.email@example.com
PUBMED_API_KEY=your_api_key_here
```

Get a free API key (optional but recommended) from NCBI:
https://www.ncbi.nlm.nih.gov/account/settings/

**Note:** The API key increases rate limits from 3 to 10 requests/second.

## Usage

### Run the scraper:

```bash
# Using uv
uv run pubmed_scraper.py

# Or activate the virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python pubmed_scraper.py
```

### Programmatic usage:

```python
from pubmed_scraper import PubMedScraper
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize scraper with credentials from .env
scraper = PubMedScraper(
    email=os.getenv('PUBMED_EMAIL'),
    api_key=os.getenv('PUBMED_API_KEY')
)

# Search and scrape
articles = scraper.scrape('neuroscience intervention learning', max_results=25)

# Save results
scraper.save_to_json(articles)
scraper.save_to_csv(articles)
```

## Fields Extracted

- PMID
- Title
- Abstract
- Authors
- Journal name
- Publication year
- DOI
- MeSH terms (keywords)
