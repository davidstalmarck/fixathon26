# Google Cloud Storage Upload Setup

Upload your PubMed data to: `gs://fixathon26-pubmed-data`

## Quick Start

### Option 1: Use gcloud CLI (Recommended)

```bash
# 1. Install dependencies
uv sync

# 2. Authenticate with Google Cloud
gcloud auth application-default login

# 3. Upload data
uv run upload_to_gcs.py
```

### Option 2: Use Service Account Key

```bash
# 1. Download your service account key from Google Cloud Console
# Save it as: gcs-key.json

# 2. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=gcs-key.json

# 3. Upload data
uv run upload_to_gcs.py
```

## What Gets Uploaded

The script uploads all your local data to GCS:

```
Local Directory                    → GCS Path
─────────────────────────────────────────────────────────────
pubmed-ids-results/               → pubmed-ids-results/
  ├── results_*.json              → results_*.json
  ├── results_*.csv               → results_*.csv
  └── aggregated_results.json     → aggregated_results.json

pubmed-articles/pdfs/             → pubmed-articles/pdfs/
  └── PMC*_PMID*.pdf              → PMC*_PMID*.pdf

pubmed-articles/xmls/             → pubmed-articles/xmls/
  └── PMC*_PMID*.xml              → PMC*_PMID*.xml

pubmed-articles/summaries/        → pubmed-articles/summaries/
  ├── PMID*_PMC*.json             → PMID*_PMC*.json
  └── all_summaries_index.json    → all_summaries_index.json
```

## Features

✅ **Smart Sync**: Skips files that already exist in GCS
✅ **Progress Tracking**: Shows upload status for each file
✅ **Error Handling**: Continues on errors, reports at end
✅ **Resume Support**: Can stop and restart without re-uploading

## Usage

```bash
# Upload all data (skips existing files)
uv run upload_to_gcs.py

# Re-upload everything (force overwrite)
# Edit upload_to_gcs.py and set skip_existing=False
```

## Check Your Data

View uploaded files at:
https://console.cloud.google.com/storage/browser/fixathon26-pubmed-data

## Troubleshooting

### Error: "Bucket not found"
- Make sure bucket exists: `gs://fixathon26-pubmed-data`
- Check you have access to the bucket

### Error: "Could not authenticate"
Run: `gcloud auth application-default login`

### Error: "Permission denied"
Make sure your account has `Storage Object Admin` role on the bucket
