# PubMed Article Processing Pipeline

This folder contains all scripts for scraping, downloading, and processing PubMed articles about rumen fermentation and methane reduction.

## Pipeline Overview

```
1. Search PubMed → 2. Download Articles → 3. Process with Claude → 4. Upload to GCS
```

## Scripts

### 1. Search & Scrape

**`pubmed_scraper.py`** - Core scraper for single queries
- Uses NCBI E-utilities API (ESearch + EFetch)
- Fetches article metadata (PMID, title, abstract, etc.)
- Saves to JSON and CSV

**`batch_scraper.py`** - Process multiple search queries
- Runs 60+ different search queries
- Gets 1000 results per query
- Saves separate files for each query

**`aggregate_results.py`** - Combine and deduplicate
- Merges all query results
- Removes duplicates by PMID
- Creates aggregated_results.json

### 2. Download Full-Text Articles

**`download_articles.py`** - Download PDFs and XMLs from PMC
- Converts PMIDs to PMC IDs using ELink
- Downloads PDFs when available
- Falls back to XML full-text
- Saves to `pubmed-articles/pdfs/` and `pubmed-articles/xmls_all/`

### 3. Process with Claude AI

**`process_articles.py`** - Original sequential processor
- 4-stage Claude AI pipeline per article
- Stages: clean text, summary, molecules, topics/keywords
- Sequential processing (slow)

**`process_articles_parallel.py`** - Parallel processor
- Processes 5 articles concurrently
- 4 stages run in parallel per article
- Uses AsyncAnthropic
- Much faster than sequential

**`process_articles_fast.py`** - Rate-limit aware processor ⭐ **RECOMMENDED**
- Processes 3 articles concurrently
- Respects Anthropic API rate limits (450K tokens/min)
- Retry logic with exponential backoff
- Batch processing (100 files at a time)
- Saves to `pubmed-articles/summaries/`

### 4. Upload to Cloud

**`upload_to_gcs.py`** - Upload to Google Cloud Storage
- Uploads all data to `gs://fixathon26-pubmed-data`
- Smart sync (skips existing files)
- Uploads: IDs, PDFs, XMLs, summaries

### Testing Scripts

**`test_claude_api.py`** - Test Claude API connection
**`test_parallel.py`** - Test async Claude calls
**`test_one_article.py`** - Test single article processing

## Usage

### Full Pipeline

```bash
# 1. Search and scrape
uv run python data-pipeline/batch_scraper.py

# 2. Aggregate results
uv run python data-pipeline/aggregate_results.py

# 3. Download full-text
uv run python data-pipeline/download_articles.py

# 4. Process with Claude AI (RECOMMENDED)
uv run python data-pipeline/process_articles_fast.py

# 5. Upload to GCS
uv run python data-pipeline/upload_to_gcs.py
```

### Reprocess Failed/Bad Summaries

```bash
# Find and delete empty summaries
grep -l '"comprehensive_summary": ""' pubmed-articles/summaries/*.json | xargs rm

# Reprocess (will skip existing)
uv run python data-pipeline/process_articles_fast.py
```

### Process Single Article (Testing)

```bash
# Edit test_one_article.py to set xml_file path
uv run python data-pipeline/test_one_article.py
```

## Configuration

All scripts use environment variables from `.env`:
- `PUBMED_EMAIL` - Email for NCBI API
- `PUBMED_API_KEY` - Optional API key for higher rate limits
- `CLAUDE_API_KEY` - Anthropic API key

## Output Structure

```
pubmed-ids-results/          # Search results
├── query_*.json            # Individual query results
└── aggregated_results.json # All results deduplicated

pubmed-articles/
├── pdfs/                   # Downloaded PDFs
├── xmls/                   # Backup XMLs (1,772 files)
├── xmls_all/               # All XMLs for processing
└── summaries/              # Claude-processed analyses
    ├── PMID*_analysis.json
    └── all_analyses_index.json
```

## Current Status

- **Total articles found**: 150,815
- **XMLs downloaded**: 1,772
- **Processed summaries**: 166
- **Remaining to process**: 1,606

## Notes

### Model Used
- Claude model: `claude-sonnet-4-20250514`

### Rate Limits
- Anthropic: 450,000 input tokens/minute
- PubMed (no API key): 3 requests/second
- PubMed (with API key): 10 requests/second

### Processing Speed
- With 3 concurrent articles: ~3 articles/minute
- Average processing time: 60-280 seconds per article
- Bottleneck: Anthropic API rate limits (NOT CPU)

### Common Issues

**429 Rate Limit Errors**: Use `process_articles_fast.py` instead of the older scripts

**Empty Summaries**: Delete and reprocess those specific files

**Wrong Article Content**: Check if article is about rumen fermentation vs other topics
