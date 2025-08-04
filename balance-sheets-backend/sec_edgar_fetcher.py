"""SEC EDGAR fetcher for 10-K reports"""
import requests
import logging
from typing import Dict, Optional
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SECEdgarFetcher:
    """Fetch 10-K reports directly from SEC EDGAR"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': 'BalanceSheetsApp/1.0 (contact@example.com)'  # SEC requires this
        }
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) for a company ticker"""
        try:
            # SEC provides a mapping file
            url = f"{self.base_url}/submissions/CIK{ticker}.json"
            
            # Try the company tickers endpoint
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(tickers_url, headers=self.headers)
            response.raise_for_status()
            
            tickers_data = response.json()
            
            # Find the CIK for the given ticker
            for item in tickers_data.values():
                if item.get('ticker') == ticker:
                    # CIK needs to be 10 digits with leading zeros
                    cik = str(item.get('cik_str')).zfill(10)
                    logger.info(f"Found CIK for {ticker}: {cik}")
                    return cik
            
            logger.error(f"CIK not found for ticker {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting CIK: {e}")
            return None
    
    def get_recent_10k_url(self, ticker: str) -> Optional[Dict[str, str]]:
        """Get the URL of the most recent 10-K filing"""
        try:
            # Get CIK first
            cik = self.get_cik(ticker)
            if not cik:
                return None
            
            # Get company submissions
            submissions_url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = requests.get(submissions_url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Find recent 10-K filings
            recent_filings = data.get('filings', {}).get('recent', {})
            
            # Look for 10-K forms
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            primary_documents = recent_filings.get('primaryDocument', [])
            
            # Find the most recent 10-K
            for i, form in enumerate(forms):
                if form == '10-K':
                    accession = accession_numbers[i].replace('-', '')
                    primary_doc = primary_documents[i]
                    filing_date = filing_dates[i]
                    
                    # Construct URLs
                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{primary_doc}"
                    filing_detail_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{accession_numbers[i]}-index.html"
                    
                    logger.info(f"Found 10-K filed on {filing_date}")
                    
                    return {
                        'filing_date': filing_date,
                        'accession_number': accession_numbers[i],
                        'document_url': filing_url,
                        'filing_detail_url': filing_detail_url,
                        'cik': cik
                    }
            
            logger.error("No 10-K filing found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting 10-K URL: {e}")
            return None
    
    def download_10k(self, ticker: str) -> Optional[str]:
        """Download the most recent 10-K filing"""
        try:
            # Get filing info
            filing_info = self.get_recent_10k_url(ticker)
            if not filing_info:
                return None
            
            logger.info(f"Downloading 10-K from: {filing_info['document_url']}")
            
            # Download the document
            response = requests.get(filing_info['document_url'], headers=self.headers)
            response.raise_for_status()
            
            # Save to file
            filename = f"{ticker}_10K_{filing_info['filing_date']}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Downloaded 10-K to {filename}")
            logger.info(f"Filing detail page: {filing_info['filing_detail_url']}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error downloading 10-K: {e}")
            return None


def test_microsoft_10k():
    """Test fetching Microsoft's most recent 10-K"""
    fetcher = SECEdgarFetcher()
    
    logger.info("\nFetching Microsoft's most recent 10-K...")
    logger.info("="*50)
    
    # Get filing info
    filing_info = fetcher.get_recent_10k_url("MSFT")
    if filing_info:
        logger.info("\n10-K Filing Information:")
        logger.info(f"  Filing Date: {filing_info['filing_date']}")
        logger.info(f"  Accession Number: {filing_info['accession_number']}")
        logger.info(f"  Document URL: {filing_info['document_url']}")
        logger.info(f"  Filing Detail URL: {filing_info['filing_detail_url']}")
        
        # Download the 10-K
        logger.info("\nDownloading 10-K document...")
        filename = fetcher.download_10k("MSFT")
        
        if filename:
            logger.info(f"\n✓ Successfully downloaded Microsoft's 10-K")
            logger.info(f"  Saved to: {filename}")
            
            # Check file size
            import os
            file_size = os.path.getsize(filename)
            logger.info(f"  File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        else:
            logger.error("\n✗ Failed to download 10-K")
    else:
        logger.error("\n✗ Failed to get 10-K filing information")


if __name__ == "__main__":
    test_microsoft_10k()