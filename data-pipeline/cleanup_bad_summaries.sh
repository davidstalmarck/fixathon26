#!/bin/bash
# Delete summaries with issues

echo 'Deleting 8 bad summaries...'

rm -f pubmed-articles/summaries/PMID11852686_analysis.json
rm -f pubmed-articles/summaries/PMID21415423_analysis.json
rm -f pubmed-articles/summaries/PMID30146293_analysis.json
rm -f pubmed-articles/summaries/PMID33372654_analysis.json
rm -f pubmed-articles/summaries/PMID35334393_analysis.json
rm -f pubmed-articles/summaries/PMID35565632_analysis.json
rm -f pubmed-articles/summaries/PMID39833301_analysis.json
rm -f pubmed-articles/summaries/PMID41302506_analysis.json

echo 'Done! Run process_articles_fast.py to reprocess.'
