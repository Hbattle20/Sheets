"""Batch fetch companies with historical data"""
from fetch_historical import HistoricalDataPipeline
from database import Database
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top 20 companies by market cap (diverse sectors)
COMPANIES_TO_FETCH = [
    'AAPL',   # Apple - Technology
    'GOOGL',  # Alphabet - Technology
    'AMZN',   # Amazon - Consumer Cyclical
    'NVDA',   # NVIDIA - Technology
    'META',   # Meta - Technology
    'TSLA',   # Tesla - Consumer Cyclical
    'BRK.B',  # Berkshire Hathaway - Financial
    'LLY',    # Eli Lilly - Healthcare
    'V',      # Visa - Financial Services
    'JPM',    # JPMorgan Chase - Financial
    'WMT',    # Walmart - Consumer Defensive
    'MA',     # Mastercard - Financial Services
    'JNJ',    # Johnson & Johnson - Healthcare
    'XOM',    # Exxon Mobil - Energy
    'PG',     # Procter & Gamble - Consumer Defensive
    'HD',     # Home Depot - Consumer Cyclical
    'COST',   # Costco - Consumer Defensive
    'ABBV',   # AbbVie - Healthcare
    'ORCL',   # Oracle - Technology
    'MRK'     # Merck - Healthcare
]

def main():
    pipeline = HistoricalDataPipeline()
    db = Database()
    
    # Check starting API calls
    starting_calls = db.get_api_calls_today()
    logger.info(f"Starting with {starting_calls}/250 API calls used today")
    
    # Estimate: 5 years × 3 statements = 15 API calls per company
    # 20 companies × 15 calls = 300 calls (but we only have 242 left)
    # So we'll monitor and stop when approaching limit
    
    successful = []
    failed = []
    
    for i, ticker in enumerate(COMPANIES_TO_FETCH, 1):
        # Check API limit before each company
        calls_used = db.get_api_calls_today()
        calls_remaining = 250 - calls_used
        
        if calls_remaining < 20:  # Need at least 20 calls for safety
            logger.warning(f"Approaching API limit ({calls_used}/250). Stopping batch.")
            break
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {i}/{len(COMPANIES_TO_FETCH)}: {ticker}")
        logger.info(f"API calls remaining: {calls_remaining}")
        logger.info(f"{'='*60}")
        
        try:
            # Fetch 5 years of annual data only (no quarters to save API calls)
            success = pipeline.fetch_historical_data(
                ticker, 
                years=5, 
                include_quarters=False
            )
            
            if success:
                successful.append(ticker)
                logger.info(f"✅ Successfully fetched {ticker}")
            else:
                failed.append(ticker)
                logger.error(f"❌ Failed to fetch {ticker}")
                
        except Exception as e:
            logger.error(f"❌ Error processing {ticker}: {e}")
            failed.append(ticker)
        
        # Be respectful to the API
        time.sleep(2)
    
    # Final summary
    final_calls = db.get_api_calls_today()
    logger.info(f"\n{'='*60}")
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Successful: {len(successful)} companies - {', '.join(successful)}")
    logger.info(f"Failed: {len(failed)} companies - {', '.join(failed) if failed else 'None'}")
    logger.info(f"Total API calls used: {final_calls - starting_calls}")
    logger.info(f"Total calls today: {final_calls}/250")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()