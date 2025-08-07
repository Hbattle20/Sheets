"""Fetch historical data for Kyndryl Holdings"""
from fetch_historical import HistoricalDataPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_kyndryl_data():
    """Fetch all available historical data for Kyndryl"""
    pipeline = HistoricalDataPipeline()
    
    logger.info("Fetching historical data for Kyndryl Holdings (KD)...")
    logger.info("Note: Kyndryl spun off from IBM in November 2021")
    logger.info("Historical data includes pro-forma financials from when it was part of IBM")
    
    try:
        # Fetch 10 years of data (will get whatever is available)
        success = pipeline.fetch_historical_data('KD', years=10, include_quarters=False)
        
        if success:
            logger.info("Successfully fetched historical data for Kyndryl")
            
            # Check what we have now
            from database import Database
            db = Database()
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            fs.report_type,
                            fs.period_end_date,
                            fs.revenue,
                            fs.net_income
                        FROM financial_snapshots fs
                        JOIN companies c ON fs.company_id = c.id
                        WHERE c.ticker = 'KD'
                        ORDER BY fs.period_end_date DESC
                    """)
                    
                    results = cur.fetchall()
                    logger.info(f"\nNow have {len(results)} financial snapshots for Kyndryl:")
                    for report_type, date, revenue, net_income in results:
                        revenue_b = revenue / 1e9 if revenue else 0
                        income_b = net_income / 1e9 if net_income else 0
                        logger.info(f"  {date} ({report_type}): Revenue ${revenue_b:.1f}B, Net Income ${income_b:.2f}B")
        else:
            logger.error("Failed to fetch historical data")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    fetch_kyndryl_data()