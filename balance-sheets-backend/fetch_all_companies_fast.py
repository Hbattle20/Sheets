"""
Fast parallel fetching for premium tier (750 calls/minute)
Optimized for maximum throughput
"""
import asyncio
import aiohttp
import time
import logging
import json
from typing import List, Dict, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

from database import Database
from pipeline import DataPipeline
from fetch_historical import HistoricalDataPipeline
from config import FMP_API_KEY, FMP_BASE_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastCompanyCollector:
    """Maximizes API usage with parallel requests"""
    
    def __init__(self):
        self.db = Database()
        self.pipeline = DataPipeline()
        self.historical_pipeline = HistoricalDataPipeline()
        self.api_key = FMP_API_KEY
        self.base_url = FMP_BASE_URL
        
        # Rate limiting
        self.calls_this_minute = 0
        self.minute_start = time.time()
        self.rate_limit = 750
        self.lock = threading.Lock()
        
        # Progress tracking
        self.processed_companies = set()
        self.failed_companies = []
        self.total_api_calls = 0
        
    async def fetch_all_tickers(self) -> List[str]:
        """Fetch all available US stock tickers including microcaps"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/stock/list?apikey={self.api_key}"
            async with session.get(url) as response:
                data = await response.json()
                
        # Filter for US stocks only (including OTC for microcaps)
        # Exclude ETFs, mutual funds, and other non-company securities
        us_exchanges = ['NYSE', 'NASDAQ', 'AMEX', 'OTC', 'OTCBB', 'PINK', 'OTCQX', 'OTCQB']
        excluded_keywords = ['ETF', 'Fund', 'Trust', 'ETN', 'Note', 'LP', 'L.P.', 'REIT']
        
        us_stocks = []
        for stock in data:
            # Check if it's a US exchange
            if stock.get('exchangeShortName') not in us_exchanges:
                continue
                
            # Must be type 'stock'
            if stock.get('type') != 'stock':
                continue
                
            # Exclude ETFs and funds based on name
            name = stock.get('name', '')
            if any(keyword in name for keyword in excluded_keywords):
                continue
                
            # Additional ETF check - they often have 'etf' in symbol
            symbol = stock.get('symbol', '')
            if 'ETF' in symbol.upper():
                continue
                
            us_stocks.append(symbol)
        
        # Log breakdown by exchange
        exchange_counts = {}
        for stock in data:
            if stock.get('symbol') in us_stocks:
                exchange = stock.get('exchangeShortName', 'Unknown')
                exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
                
        logger.info(f"Found {len(us_stocks)} US company stocks")
        for exchange, count in sorted(exchange_counts.items()):
            logger.info(f"  {exchange}: {count} stocks")
            
        return us_stocks
        
    def check_rate_limit(self, calls_needed: int = 1) -> bool:
        """Check if we can make more calls without exceeding limit"""
        with self.lock:
            current_time = time.time()
            
            # Reset counter if minute has passed
            if current_time - self.minute_start >= 60:
                self.calls_this_minute = 0
                self.minute_start = current_time
                
            # Check if we have capacity
            if self.calls_this_minute + calls_needed <= self.rate_limit:
                self.calls_this_minute += calls_needed
                self.total_api_calls += calls_needed
                return True
            return False
            
    def wait_for_rate_limit(self, calls_needed: int = 1):
        """Wait if necessary for rate limit"""
        while not self.check_rate_limit(calls_needed):
            time.sleep(0.1)  # Check every 100ms
            
    def process_company_with_history(self, ticker: str) -> bool:
        """Process a single company with all historical data"""
        try:
            # API calls needed: 
            # - Current data: 6 calls
            # - Historical (10 years annual): 30 calls
            total_calls = 36
            
            # Wait for rate limit
            self.wait_for_rate_limit(total_calls)
            
            # Process current data
            success = self.pipeline.process_company(ticker)
            
            if success:
                # Fetch 10 years of historical data
                self.historical_pipeline.fetch_historical_data(
                    ticker,
                    years=10,
                    include_quarters=False  # Annual only
                )
                
                logger.info(f"✓ {ticker} - Complete with 10 years history")
                return True
            else:
                logger.warning(f"✗ {ticker} - Failed current data")
                return False
                
        except Exception as e:
            logger.error(f"✗ {ticker} - Error: {str(e)}")
            return False
            
    def parallel_process_companies(self, tickers: List[str], max_workers: int = 20):
        """Process companies in parallel using thread pool"""
        logger.info(f"Processing {len(tickers)} companies with {max_workers} workers...")
        
        # Get existing companies
        existing = self.get_existing_companies()
        new_tickers = [t for t in tickers if t not in existing]
        logger.info(f"Found {len(new_tickers)} new companies to process")
        
        # Track progress
        completed = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for ticker in new_tickers:
                future = executor.submit(self.process_company_with_history, ticker)
                futures.append((ticker, future))
                
            # Process results as they complete
            for ticker, future in futures:
                try:
                    success = future.result()
                    if success:
                        self.processed_companies.add(ticker)
                    else:
                        self.failed_companies.append(ticker)
                except Exception as e:
                    logger.error(f"Exception processing {ticker}: {e}")
                    self.failed_companies.append(ticker)
                    
                completed += 1
                
                # Progress update every 50 companies
                if completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed * 60  # Companies per minute
                    api_rate = self.total_api_calls / elapsed * 60  # API calls per minute
                    
                    logger.info(f"""
Progress: {completed}/{len(new_tickers)} companies
Rate: {rate:.1f} companies/min, {api_rate:.1f} API calls/min
Estimated time remaining: {(len(new_tickers) - completed) / rate:.1f} minutes
                    """)
                    
                    # Save progress
                    self.save_progress()
                    
        # Final summary
        elapsed = time.time() - start_time
        logger.info(f"""
=== COLLECTION COMPLETE ===
Total time: {elapsed/60:.1f} minutes
Companies processed: {len(self.processed_companies)}
Failed: {len(self.failed_companies)}
Total API calls: {self.total_api_calls:,}
Average API rate: {self.total_api_calls/elapsed*60:.1f} calls/min
        """)
        
    def get_existing_companies(self) -> Set[str]:
        """Get tickers already in database"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ticker FROM companies")
                return {row[0] for row in cur.fetchall()}
                
    def save_progress(self):
        """Save current progress to file"""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'processed': list(self.processed_companies),
            'failed': self.failed_companies,
            'total_api_calls': self.total_api_calls,
            'stats': self.get_stats()
        }
        
        with open('fast_collection_progress.json', 'w') as f:
            json.dump(progress, f, indent=2)
            
    def get_stats(self) -> Dict:
        """Get current statistics"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT c.id) as total_companies,
                        COUNT(DISTINCT fs.id) as total_snapshots,
                        COUNT(DISTINCT CASE WHEN fs.period_end_date < CURRENT_DATE - INTERVAL '1 year' 
                                           THEN c.id END) as companies_with_history
                    FROM companies c
                    LEFT JOIN financial_snapshots fs ON c.id = fs.company_id
                """)
                stats = cur.fetchone()
                
        return {
            'total_companies': stats[0],
            'total_snapshots': stats[1],
            'companies_with_history': stats[2]
        }
        
    async def run_async(self):
        """Main async entry point"""
        # Get all available tickers
        all_tickers = await self.fetch_all_tickers()
        
        # Save ticker list
        with open('all_us_stocks.txt', 'w') as f:
            f.write('\n'.join(all_tickers))
        logger.info(f"Saved {len(all_tickers)} tickers to all_us_stocks.txt")
        
        # Process in parallel
        self.parallel_process_companies(all_tickers, max_workers=20)
        
        # Save final results
        self.save_progress()
        
        if self.failed_companies:
            with open('failed_tickers.txt', 'w') as f:
                f.write('\n'.join(self.failed_companies))
            logger.info(f"Saved {len(self.failed_companies)} failed tickers to failed_tickers.txt")


def main():
    """Run the fast collector"""
    collector = FastCompanyCollector()
    
    # Run the async collector
    asyncio.run(collector.run_async())
    
    # Show final stats
    stats = collector.get_stats()
    logger.info(f"""
=== FINAL DATABASE STATS ===
Total companies: {stats['total_companies']:,}
Total snapshots: {stats['total_snapshots']:,}
Companies with historical data: {stats['companies_with_history']:,}
    """)


if __name__ == '__main__':
    main()