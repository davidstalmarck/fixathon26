#!/usr/bin/env python3
"""
Upload PubMed Data to Google Cloud Storage
Syncs local files to GCS bucket: gs://fixathon26-pubmed-data
"""

import os
from pathlib import Path
from typing import List, Optional
from google.cloud import storage
from datetime import datetime

# GCS Configuration
BUCKET_NAME = "fixathon26-pubmed-data"

# Local directories to upload
UPLOAD_DIRS = {
    "pubmed-ids-results": "pubmed-ids-results",  # local -> GCS path
    "pubmed-articles/pdfs": "pubmed-articles/pdfs",
    "pubmed-articles/xmls": "pubmed-articles/xmls",
    "pubmed-articles/summaries": "pubmed-articles/summaries",
}


class GCSUploader:
    """Upload files to Google Cloud Storage"""

    def __init__(self, bucket_name: str):
        """
        Initialize GCS client

        Args:
            bucket_name: Name of the GCS bucket
        """
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name

    def file_exists_in_gcs(self, gcs_path: str) -> bool:
        """
        Check if file exists in GCS

        Args:
            gcs_path: Path in GCS bucket

        Returns:
            True if exists, False otherwise
        """
        blob = self.bucket.blob(gcs_path)
        return blob.exists()

    def upload_file(self, local_path: Path, gcs_path: str, skip_existing: bool = True) -> bool:
        """
        Upload a single file to GCS

        Args:
            local_path: Local file path
            gcs_path: Destination path in GCS
            skip_existing: Skip if file already exists in GCS

        Returns:
            True if uploaded, False if skipped or error
        """
        # Check if file exists in GCS
        if skip_existing and self.file_exists_in_gcs(gcs_path):
            print(f"  ⏭️  Skipping (already exists): {gcs_path}")
            return False

        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(str(local_path))
            print(f"  ✓ Uploaded: {gcs_path}")
            return True
        except Exception as e:
            print(f"  ✗ Error uploading {gcs_path}: {e}")
            return False

    def upload_directory(self, local_dir: Path, gcs_prefix: str,
                        pattern: str = "*", skip_existing: bool = True) -> tuple:
        """
        Upload all files in a directory to GCS

        Args:
            local_dir: Local directory path
            gcs_prefix: Prefix for GCS paths
            pattern: File pattern to match (e.g., "*.json", "*.pdf")
            skip_existing: Skip files that already exist in GCS

        Returns:
            Tuple of (uploaded_count, skipped_count, error_count)
        """
        if not local_dir.exists():
            print(f"⚠️  Directory not found: {local_dir}")
            return (0, 0, 0)

        print(f"\nUploading from: {local_dir}")
        print(f"To GCS prefix: gs://{self.bucket_name}/{gcs_prefix}")

        uploaded = 0
        skipped = 0
        errors = 0

        # Get all files matching pattern
        files = list(local_dir.glob(pattern))
        if not files:
            print(f"  No files found matching pattern: {pattern}")
            return (0, 0, 0)

        print(f"Found {len(files)} files")

        for local_file in files:
            # Create GCS path
            relative_path = local_file.relative_to(local_dir)
            gcs_path = f"{gcs_prefix}/{relative_path}"

            # Upload file
            result = self.upload_file(local_file, gcs_path, skip_existing)

            if result:
                uploaded += 1
            elif skip_existing and self.file_exists_in_gcs(gcs_path):
                skipped += 1
            else:
                errors += 1

        return (uploaded, skipped, errors)

    def sync_all_data(self, skip_existing: bool = True):
        """
        Sync all local data directories to GCS

        Args:
            skip_existing: Skip files that already exist in GCS
        """
        print("="*80)
        print(f"Syncing Data to GCS: gs://{self.bucket_name}")
        print("="*80)

        total_uploaded = 0
        total_skipped = 0
        total_errors = 0

        # Upload each directory
        for local_dir_str, gcs_prefix in UPLOAD_DIRS.items():
            local_dir = Path(local_dir_str)

            uploaded, skipped, errors = self.upload_directory(
                local_dir,
                gcs_prefix,
                pattern="**/*" if local_dir.is_dir() else "*",
                skip_existing=skip_existing
            )

            total_uploaded += uploaded
            total_skipped += skipped
            total_errors += errors

        # Summary
        print("\n" + "="*80)
        print("Upload Summary")
        print("="*80)
        print(f"Total files uploaded: {total_uploaded}")
        print(f"Total files skipped: {total_skipped}")
        print(f"Total errors: {total_errors}")
        print(f"\nBucket URL: https://console.cloud.google.com/storage/browser/{self.bucket_name}")
        print("="*80)


def main():
    """Main upload workflow"""
    print("="*80)
    print("PubMed Data Upload to Google Cloud Storage")
    print("="*80 + "\n")

    # Check for Google Cloud credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        print("   Attempting to use default credentials...\n")

    try:
        # Initialize uploader
        uploader = GCSUploader(BUCKET_NAME)

        # Test bucket access
        print(f"Testing access to bucket: {BUCKET_NAME}")
        if uploader.bucket.exists():
            print(f"✓ Bucket accessible: gs://{BUCKET_NAME}\n")
        else:
            print(f"✗ Bucket not found: {BUCKET_NAME}")
            return

        # Sync all data
        uploader.sync_all_data(skip_existing=True)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"\nMake sure you're authenticated with Google Cloud:")
        print("  gcloud auth application-default login")
        print("\nOr set GOOGLE_APPLICATION_CREDENTIALS to your service account key:")
        print("  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")


if __name__ == '__main__':
    main()
