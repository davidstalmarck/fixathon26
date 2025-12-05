#!/usr/bin/env python3
"""
PubMed Scraper using NCBI E-utilities API
Searches for articles and retrieves detailed metadata
"""

import requests
import time
import json
import csv
import os
from typing import List, Dict, Optional
from pprint import pprint
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class PubMedScraper:
    """Scraper for PubMed articles using E-utilities API"""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the scraper

        Args:
            email: Your email (recommended by NCBI)
            api_key: NCBI API key (optional, increases rate limit)
        """
        self.email = email
        self.api_key = api_key
        self.rate_limit_delay = 0.34 if not api_key else 0.1  # 3 req/s or 10 req/s with key

    def search(self, query: str, max_results: int = 100) -> List[str]:
        """
        Search PubMed for articles matching the query

        Args:
            query: Search term(s)
            max_results: Maximum number of results to return

        Returns:
            List of PMIDs
        """
        params = {
            'db': 'pubmed',
            'term': query,
            'retmode': 'json',
            'retmax': max_results
        }

        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key

        try:
            response = requests.get(self.ESEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

            pmids = data.get('esearchresult', {}).get('idlist', [])
            print(f"Found {len(pmids)} articles")
            return pmids

        except requests.exceptions.RequestException as e:
            print(f"Search error: {e}")
            return []

    def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch detailed article information for given PMIDs

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of article dictionaries with parsed metadata
        """
        if not pmids:
            return []

        # EFetch returns XML format for detailed data
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml'
        }

        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key

        try:
            time.sleep(self.rate_limit_delay)  # Respect rate limits
            response = requests.get(self.EFETCH_URL, params=params)
            response.raise_for_status()

            return self._parse_xml_response(response.text)

        except requests.exceptions.RequestException as e:
            print(f"Fetch error: {e}")
            return []

    def _parse_xml_response(self, xml_text: str) -> List[Dict]:
        """Parse XML response from EFetch into structured data"""
        articles = []
        root = ET.fromstring(xml_text)

        for article_elem in root.findall('.//PubmedArticle'):
            try:
                article_data = self._extract_article_data(article_elem)
                articles.append(article_data)
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        return articles

    def _extract_article_data(self, article_elem: ET.Element) -> Dict:
        """Extract relevant fields from a PubmedArticle XML element"""
        medline = article_elem.find('.//MedlineCitation')
        article = medline.find('.//Article')

        # Basic article info
        pmid = medline.find('.//PMID').text if medline.find('.//PMID') is not None else ''
        title = article.find('.//ArticleTitle').text if article.find('.//ArticleTitle') is not None else ''

        # Abstract
        abstract_elem = article.find('.//Abstract/AbstractText')
        abstract = abstract_elem.text if abstract_elem is not None else ''

        # Authors
        authors = []
        for author in article.findall('.//Author'):
            last_name = author.find('LastName')
            fore_name = author.find('ForeName')
            if last_name is not None and fore_name is not None:
                authors.append(f"{fore_name.text} {last_name.text}")

        # Journal info
        journal = article.find('.//Journal/Title')
        journal_name = journal.text if journal is not None else ''

        # Publication date
        pub_date = article.find('.//Journal/JournalIssue/PubDate')
        year = pub_date.find('Year').text if pub_date is not None and pub_date.find('Year') is not None else ''

        # DOI
        doi = ''
        for article_id in article_elem.findall('.//ArticleId'):
            if article_id.get('IdType') == 'doi':
                doi = article_id.text
                break

        # Keywords/MeSH terms
        mesh_terms = []
        for mesh in medline.findall('.//MeshHeading/DescriptorName'):
            mesh_terms.append(mesh.text)

        return {
            'pmid': pmid,
            'title': title,
            'abstract': abstract,
            'authors': ', '.join(authors),
            'journal': journal_name,
            'year': year,
            'doi': doi,
            'mesh_terms': '; '.join(mesh_terms)
        }

    def scrape(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Main method to search and fetch article details

        Args:
            query: Search term(s)
            max_results: Maximum number of results

        Returns:
            List of article dictionaries
        """
        print(f"Searching PubMed for: '{query}'")
        pmids = self.search(query, max_results)

        if not pmids:
            print("No results found")
            return []

        print(f"Fetching details for {len(pmids)} articles...")
        articles = self.fetch_details(pmids)
        print(f"Successfully retrieved {len(articles)} articles")

        return articles

    def save_to_json(self, articles: List[Dict], filename: str = 'pubmed_results.json'):
        """Save articles to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(articles)} articles to {filename}")

    def save_to_csv(self, articles: List[Dict], filename: str = 'pubmed_results.csv'):
        """Save articles to CSV file"""
        if not articles:
            print("No articles to save")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=articles[0].keys())
            writer.writeheader()
            writer.writerows(articles)
        print(f"Saved {len(articles)} articles to {filename}")


def main():
    """Example usage"""
    # Load credentials from environment variables
    email = os.getenv('PUBMED_EMAIL')
    api_key = os.getenv('PUBMED_API_KEY')

    # Initialize scraper with credentials from .env
    scraper = PubMedScraper(email=email, api_key=api_key)

    # Search and scrape
    query = 'neuroscience intervention learning'
    articles = scraper.scrape(query, max_results=100)

    # Display first article
    if articles:
        print("\nFirst article:")
        pprint(articles[0])

        # Save results
        scraper.save_to_json(articles)
        scraper.save_to_csv(articles)


if __name__ == '__main__':
    main()