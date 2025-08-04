#!/usr/bin/env python3
"""
Process multiple years of 10-K documents for a company.
Downloads and processes the last N years of 10-K filings.
"""

import os
import time
import logging
from datetime import datetime
from process_10k_improved import ImprovedSEC10KProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiYear10KProcessor:
    """Process multiple years of 10-K documents"""
    
    def __init__(self):
        self.processor = ImprovedSEC10KProcessor()
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': 'BalanceSheetsApp/1.0 (contact@example.com)',
            'Accept': 'application/json'
        }
    
    def get_multiple_10k_urls(self, ticker: str, years: int = 5):
        """Get URLs for multiple years of 10-K filings"""
        try:
            cik = self.processor.get_cik(ticker)
            if not cik:
                return []
            
            # Get company submissions
            submissions_url = f"{self.base_url}/submissions/CIK{cik}.json"
            import requests
            response = requests.get(submissions_url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            recent_filings = data.get('filings', {}).get('recent', {})
            
            # Find 10-K forms
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            
            ten_k_filings = []
            
            for i, form in enumerate(forms):
                if form == '10-K' and len(ten_k_filings) < years:
                    accession = accession_numbers[i]
                    accession_clean = accession.replace('-', '')
                    cik_clean = cik.lstrip('0')
                    
                    base_filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession_clean}"
                    
                    filing_info = {
                        'ticker': ticker,
                        'filing_date': filing_dates[i],
                        'year': filing_dates[i][:4],
                        'accession': accession,
                        'txt_url': f"{base_filing_url}/{accession}.txt",
                        'html_url': f"{base_filing_url}/{accession}-index.html"
                    }
                    
                    ten_k_filings.append(filing_info)
                    logger.info(f"Found 10-K for {filing_info['year']} filed on {filing_info['filing_date']}")
            
            return ten_k_filings
            
        except Exception as e:
            logger.error(f"Error getting multiple 10-K URLs: {e}")
            return []
    
    def process_multiple_years(self, ticker: str, years: int = 5, output_dir: str = 'output'):
        """Process multiple years of 10-K filings"""
        logger.info(f"\nProcessing {years} years of 10-K filings for {ticker}")
        logger.info("=" * 60)
        
        # Get filing URLs
        filings = self.get_multiple_10k_urls(ticker, years)
        
        if not filings:
            logger.error("No 10-K filings found")
            return
        
        logger.info(f"\nFound {len(filings)} 10-K filings to process")
        
        # Create year-specific output directories
        base_output_dir = output_dir
        
        results = []
        
        for i, filing in enumerate(filings):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {i+1}/{len(filings)}: {filing['year']} 10-K")
            logger.info(f"{'='*60}")
            
            # Create year-specific directory
            year_output_dir = os.path.join(base_output_dir, f"{ticker}_{filing['year']}")
            os.makedirs(year_output_dir, exist_ok=True)
            
            # Temporarily modify the processor's URLs
            original_get_recent = self.processor.get_recent_10k_urls
            
            # Create a custom URL getter for this specific filing
            def get_specific_filing(t):
                return filing
            
            self.processor.get_recent_10k_urls = get_specific_filing
            
            try:
                # Process the filing
                success = self.processor.process_10k(ticker, year_output_dir)
                
                if success:
                    results.append({
                        'year': filing['year'],
                        'filing_date': filing['filing_date'],
                        'status': 'success',
                        'output_dir': year_output_dir
                    })
                    logger.info(f"✓ Successfully processed {filing['year']} 10-K")
                else:
                    results.append({
                        'year': filing['year'],
                        'filing_date': filing['filing_date'],
                        'status': 'failed',
                        'output_dir': year_output_dir
                    })
                    logger.error(f"✗ Failed to process {filing['year']} 10-K")
                
            except Exception as e:
                logger.error(f"Error processing {filing['year']} 10-K: {e}")
                results.append({
                    'year': filing['year'],
                    'filing_date': filing['filing_date'],
                    'status': 'error',
                    'error': str(e),
                    'output_dir': year_output_dir
                })
            
            finally:
                # Restore original method
                self.processor.get_recent_10k_urls = original_get_recent
            
            # Be respectful to SEC servers
            if i < len(filings) - 1:
                logger.info("Waiting 2 seconds before next request...")
                time.sleep(2)
        
        # Summary report
        logger.info(f"\n{'='*60}")
        logger.info("PROCESSING SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total filings processed: {len(results)}")
        
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] != 'success']
        
        logger.info(f"Successful: {len(successful)}")
        logger.info(f"Failed: {len(failed)}")
        
        if successful:
            logger.info("\nSuccessfully processed:")
            for r in successful:
                logger.info(f"  - {r['year']} (filed {r['filing_date']}): {r['output_dir']}")
        
        if failed:
            logger.info("\nFailed to process:")
            for r in failed:
                error_msg = r.get('error', 'Unknown error')
                logger.info(f"  - {r['year']}: {error_msg}")
        
        # Create a summary file
        summary_file = os.path.join(base_output_dir, f"{ticker}_multi_year_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(summary_file, 'w') as f:
            f.write(f"Multi-Year 10-K Processing Summary for {ticker}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Processing Date: {datetime.now().isoformat()}\n")
            f.write(f"Years Requested: {years}\n")
            f.write(f"Filings Found: {len(filings)}\n")
            f.write(f"Successfully Processed: {len(successful)}\n\n")
            
            if successful:
                f.write("Processed Filings:\n")
                for r in successful:
                    f.write(f"  - {r['year']} (filed {r['filing_date']})\n")
                    f.write(f"    Output: {r['output_dir']}\n")
        
        logger.info(f"\nSummary saved to: {summary_file}")
        
        return results


def main():
    """Process last 5 years of Microsoft 10-Ks"""
    processor = MultiYear10KProcessor()
    
    # Process Microsoft's last 5 years of 10-Ks
    results = processor.process_multiple_years('MSFT', years=5)


if __name__ == "__main__":
    main()