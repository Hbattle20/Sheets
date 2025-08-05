"""
Fetch all available companies from FMP and collect 10 years of historical data
Premium tier: 750 calls/minute
"""
import time
import logging
from typing import List, Dict, Set
from datetime import datetime
from collections import defaultdict

from fetcher import FMPClient
from database import Database
from fetch_historical import HistoricalDataPipeline
from pipeline import DataPipeline
from config import FMP_CALLS_PER_BATCH, FMP_RATE_LIMIT_PER_MINUTE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyDataCollector:
    """Collects all available company data with rate limiting"""
    
    def __init__(self):
        self.fmp_client = FMPClient()
        self.db = Database()
        self.pipeline = DataPipeline()
        self.historical_pipeline = HistoricalDataPipeline()
        self.calls_this_minute = 0
        self.minute_start = time.time()
        
    def _rate_limit_check(self, calls_needed: int = 1):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = current_time
            
        # If we would exceed the limit, wait
        if self.calls_this_minute + calls_needed > FMP_CALLS_PER_BATCH:
            wait_time = 60 - (current_time - self.minute_start)
            logger.info(f"Rate limit approaching. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time + 1)  # Extra second for safety
            self.calls_this_minute = 0
            self.minute_start = time.time()
            
        self.calls_this_minute += calls_needed
        
    def get_all_available_tickers(self) -> List[str]:
        """Fetch list of all available stock tickers from FMP"""
        logger.info("Fetching all available tickers from FMP...")
        
        # FMP endpoints for different exchanges
        exchanges = ['NYSE', 'NASDAQ', 'AMEX']
        all_tickers = []
        
        for exchange in exchanges:
            self._rate_limit_check(1)
            try:
                # Get stock list for exchange
                data = self.fmp_client._make_request(f'available-traded/list', 
                                                   params={'exchange': exchange})
                tickers = [item['symbol'] for item in data if item.get('type') == 'stock']
                all_tickers.extend(tickers)
                logger.info(f"Found {len(tickers)} stocks on {exchange}")
            except Exception as e:
                logger.error(f"Error fetching {exchange} tickers: {e}")
                
        # Alternative: Get all active stocks
        self._rate_limit_check(1)
        try:
            active_stocks = self.fmp_client._make_request('stock/list')
            active_tickers = [stock['symbol'] for stock in active_stocks 
                            if stock.get('type') == 'stock' and stock.get('exchangeShortName') in ['NYSE', 'NASDAQ', 'AMEX']]
            
            # Merge and deduplicate
            all_tickers = list(set(all_tickers + active_tickers))
            
        except Exception as e:
            logger.error(f"Error fetching active stocks: {e}")
            
        logger.info(f"Total unique tickers found: {len(all_tickers)}")
        return sorted(all_tickers)
        
    def get_existing_companies(self) -> Set[str]:
        """Get tickers already in database"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ticker FROM companies")
                return {row[0] for row in cur.fetchall()}
                
    def process_company_batch(self, tickers: List[str], skip_existing: bool = True):
        """Process a batch of companies with current and historical data"""
        existing = self.get_existing_companies() if skip_existing else set()
        
        # Track progress
        total = len(tickers)
        processed = 0
        failed = []
        
        logger.info(f"Processing {total} companies...")
        
        for ticker in tickers:
            if ticker in existing:
                logger.info(f"Skipping {ticker} - already exists")
                processed += 1
                continue
                
            try:
                # Calculate API calls needed
                # Current data: ~6 calls
                # Historical data (10 years): ~30 calls (3 per year)
                total_calls = 36
                
                self._rate_limit_check(total_calls)
                
                logger.info(f"Processing {ticker} ({processed + 1}/{total})...")
                
                # First fetch current data
                success = self.pipeline.process_company(ticker)
                
                if success:
                    # Then fetch historical data
                    self.historical_pipeline.fetch_historical_data(
                        ticker, 
                        years=10, 
                        include_quarters=False  # Annual data only to save API calls
                    )
                    logger.info(f"Successfully processed {ticker}")
                else:
                    logger.warning(f"Failed to process current data for {ticker}")
                    failed.append(ticker)
                    
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                failed.append(ticker)
                
            processed += 1
            
            # Progress update every 10 companies
            if processed % 10 == 0:
                logger.info(f"Progress: {processed}/{total} companies processed")
                
        # Summary
        logger.info(f"\nProcessing complete!")
        logger.info(f"Total processed: {processed}")
        logger.info(f"Failed: {len(failed)}")
        if failed:
            logger.info(f"Failed tickers: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
            
        return failed
        
    def collect_all_companies(self, limit: int = None):
        """Main method to collect all available companies"""
        logger.info("Starting comprehensive company data collection...")
        
        # Get all available tickers
        all_tickers = self.get_all_available_tickers()
        
        if limit:
            all_tickers = all_tickers[:limit]
            logger.info(f"Limiting to first {limit} companies")
            
        # Save ticker list for reference
        with open('all_tickers.txt', 'w') as f:
            f.write('\n'.join(all_tickers))
        logger.info(f"Saved {len(all_tickers)} tickers to all_tickers.txt")
        
        # Process in batches
        batch_size = 20  # Process 20 companies at a time
        failed_tickers = []
        
        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i + batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1}/{(len(all_tickers) + batch_size - 1)//batch_size}")
            
            failed = self.process_company_batch(batch)
            failed_tickers.extend(failed)
            
            # Save progress
            self.save_progress(i + len(batch), len(all_tickers), failed_tickers)
            
        logger.info("\nCollection complete!")
        return failed_tickers
        
    def save_progress(self, processed: int, total: int, failed: List[str]):
        """Save progress to file for recovery"""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'processed': processed,
            'total': total,
            'failed_count': len(failed),
            'failed_tickers': failed
        }
        
        with open('collection_progress.json', 'w') as f:
            import json
            json.dump(progress, f, indent=2)
            
    def get_company_stats(self):
        """Get statistics about collected data"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Company count by sector
                cur.execute("""
                    SELECT sector, COUNT(*) as count 
                    FROM companies 
                    GROUP BY sector 
                    ORDER BY count DESC
                """)
                sectors = cur.fetchall()
                
                # Total snapshots
                cur.execute("SELECT COUNT(*) FROM financial_snapshots")
                total_snapshots = cur.fetchone()[0]
                
                # Companies with historical data
                cur.execute("""
                    SELECT COUNT(DISTINCT company_id) 
                    FROM financial_snapshots 
                    WHERE period_end_date < CURRENT_DATE - INTERVAL '1 year'
                """)
                companies_with_history = cur.fetchone()[0]
                
        logger.info("\n=== Collection Statistics ===")
        logger.info(f"Total companies: {sum(count for _, count in sectors)}")
        logger.info(f"Total financial snapshots: {total_snapshots}")
        logger.info(f"Companies with historical data: {companies_with_history}")
        logger.info("\nBy Sector:")
        for sector, count in sectors:
            logger.info(f"  {sector}: {count}")


def main():
    """Run the collection process"""
    collector = CompanyDataCollector()
    
    # Option 1: Collect everything (this will take hours)
    # failed = collector.collect_all_companies()
    
    # Option 2: Start with S&P 500 companies
    sp500_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'LLY', 'V',
        'JPM', 'WMT', 'MA', 'JNJ', 'XOM', 'PG', 'HD', 'CVX', 'MRK', 'ABBV',
        'COST', 'ADBE', 'CRM', 'BAC', 'NFLX', 'AMD', 'PEP', 'TMO', 'WFC', 'DIS',
        'CSCO', 'MCD', 'ABT', 'DHR', 'INTC', 'VZ', 'INTU', 'AMGN', 'IBM', 'CMCSA',
        'NOW', 'QCOM', 'TXN', 'PM', 'HON', 'RTX', 'NEE', 'SPGI', 'COP', 'UNP',
        # Add more S&P 500 tickers as needed
    ]
    
    # Process S&P 500 first
    logger.info("Starting with S&P 500 companies...")
    failed = collector.process_company_batch(sp500_tickers, skip_existing=True)
    
    # Show statistics
    collector.get_company_stats()
    
    if failed:
        logger.info(f"\nRetry failed tickers: {', '.join(failed)}")
        

if __name__ == '__main__':
    main()