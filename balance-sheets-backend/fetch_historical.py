"""Fetch historical financial data for companies"""
import logging
from datetime import datetime
from pipeline import DataPipeline
from fetcher import FMPClient
from database import Database
from models import FinancialSnapshot, DataFetchLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalDataPipeline(DataPipeline):
    """Extended pipeline for fetching historical data"""
    
    def fetch_historical_data(self, ticker: str, years: int = 10, include_quarters: bool = True):
        """Fetch historical financial data for a company
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years of history to fetch
            include_quarters: Whether to fetch quarterly (10-Q) data in addition to annual (10-K)
        """
        logger.info(f"Starting historical data fetch for {ticker} - {years} years")
        
        # Check if company exists
        company = self.db.get_company_by_ticker(ticker)
        if not company:
            logger.info(f"Company {ticker} not found, fetching company profile first")
            success = self.process_company(ticker)
            if not success:
                logger.error(f"Failed to fetch company profile for {ticker}")
                return False
            company = self.db.get_company_by_ticker(ticker)
        
        company_id = company['id']
        
        # Calculate API calls needed
        api_calls_needed = 0
        if include_quarters:
            # 4 quarters per year + 1 annual = 5 periods per year
            # 3 API calls per period (balance sheet + income statement + cash flow)
            api_calls_needed = years * 5 * 3
        else:
            # Just annual reports
            api_calls_needed = years * 3
        
        # Check rate limit
        calls_today = self.db.get_api_calls_today()
        if calls_today + api_calls_needed > 250:
            logger.warning(f"Would exceed rate limit. Current: {calls_today}, Needed: {api_calls_needed}")
            logger.warning(f"Can only fetch {(250 - calls_today) // 2} more periods today")
            return False
        
        logger.info(f"Estimated API calls needed: {api_calls_needed}")
        
        fetch_log = DataFetchLog(
            ticker=ticker,
            fetch_timestamp=datetime.now(),
            api_calls_used=0
        )
        
        try:
            # Fetch annual data
            logger.info(f"Fetching {years} years of annual reports")
            annual_balance_sheets = self.api_client.get_balance_sheet(ticker, 'annual', years)
            fetch_log.api_calls_used += 1
            
            annual_income_statements = self.api_client.get_income_statement(ticker, 'annual', years)
            fetch_log.api_calls_used += 1
            
            annual_cash_flows = self.api_client.get_cash_flow_statement(ticker, 'annual', years)
            fetch_log.api_calls_used += 1
            
            # Process annual data
            for i, (bs, income, cf) in enumerate(zip(annual_balance_sheets, annual_income_statements, annual_cash_flows)):
                logger.info(f"Processing annual report for {bs.get('date')}")
                
                snapshot = FinancialSnapshot(
                    company_id=company_id,
                    period_end_date=datetime.strptime(bs.get('date'), '%Y-%m-%d'),
                    report_type='10-K',
                    assets=bs.get('totalAssets', 0),
                    liabilities=bs.get('totalLiabilities', 0),
                    equity=bs.get('totalStockholdersEquity', 0),
                    cash=bs.get('cashAndCashEquivalents', 0),
                    debt=bs.get('totalDebt', 0),
                    revenue=income.get('revenue', 0),
                    net_income=income.get('netIncome', 0),
                    operating_cash_flow=cf.get('operatingCashFlow', 0),
                    free_cash_flow=cf.get('freeCashFlow', 0),
                    shares_outstanding=income.get('weightedAverageShsOut', 0),
                    raw_data={'balance_sheet': bs, 'income_statement': income, 'cash_flow': cf}
                )
                
                self.db.insert_financial_snapshot(snapshot)
            
            # Fetch quarterly data if requested
            if include_quarters:
                quarters_to_fetch = years * 4
                logger.info(f"Fetching {quarters_to_fetch} quarters of data")
                
                quarterly_balance_sheets = self.api_client.get_balance_sheet(ticker, 'quarter', quarters_to_fetch)
                fetch_log.api_calls_used += 1
                
                quarterly_income_statements = self.api_client.get_income_statement(ticker, 'quarter', quarters_to_fetch)
                fetch_log.api_calls_used += 1
                
                # Process quarterly data
                for bs, income in zip(quarterly_balance_sheets, quarterly_income_statements):
                    logger.info(f"Processing quarterly report for {bs.get('date')}")
                    
                    snapshot = FinancialSnapshot(
                        company_id=company_id,
                        period_end_date=datetime.strptime(bs.get('date'), '%Y-%m-%d'),
                        report_type='10-Q',
                        assets=bs.get('totalAssets', 0),
                        liabilities=bs.get('totalLiabilities', 0),
                        equity=bs.get('totalStockholdersEquity', 0),
                        cash=bs.get('cashAndCashEquivalents', 0),
                        debt=bs.get('totalDebt', 0),
                        revenue=income.get('revenue', 0),
                        net_income=income.get('netIncome', 0),
                        shares_outstanding=income.get('weightedAverageShsOut', 0),
                        raw_data={'balance_sheet': bs, 'income_statement': income}
                    )
                    
                    self.db.insert_financial_snapshot(snapshot)
            
            fetch_log.success = True
            logger.info(f"Successfully fetched historical data for {ticker}")
            logger.info(f"Total API calls used: {fetch_log.api_calls_used}")
            
            # Print summary
            self._print_historical_summary(ticker, years, include_quarters)
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            fetch_log.success = False
            fetch_log.error_message = str(e)
            return False
            
        finally:
            self.db.log_fetch_attempt(fetch_log)
    
    def _print_historical_summary(self, ticker: str, years: int, include_quarters: bool):
        """Print summary of historical data fetched"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Count snapshots
                cur.execute("""
                    SELECT 
                        report_type,
                        COUNT(*) as count,
                        MIN(period_end_date) as earliest,
                        MAX(period_end_date) as latest
                    FROM financial_snapshots
                    WHERE company_id = (SELECT id FROM companies WHERE ticker = %s)
                    GROUP BY report_type
                """, (ticker,))
                
                results = cur.fetchall()
                
                print(f"\n{'='*60}")
                print(f"Historical Data Summary for {ticker}")
                print(f"{'='*60}")
                
                for row in results:
                    report_type, count, earliest, latest = row
                    print(f"{report_type} Reports: {count} total")
                    print(f"  Date range: {earliest} to {latest}")
                
                print(f"{'='*60}\n")


def main():
    """Example usage"""
    pipeline = HistoricalDataPipeline()
    
    # Example: Fetch 10 years of data for Apple
    # This will use approximately 100 API calls (10 years * 5 periods * 2 statements)
    # pipeline.fetch_historical_data('AAPL', years=10, include_quarters=True)
    
    # Example: Fetch just 5 years of annual data
    # This will use only 10 API calls (5 years * 1 period * 2 statements)
    # pipeline.fetch_historical_data('GOOGL', years=5, include_quarters=False)
    
    print("Historical data fetcher ready!")
    print("\nExamples:")
    print("  pipeline = HistoricalDataPipeline()")
    print("  pipeline.fetch_historical_data('AAPL', years=10, include_quarters=True)")
    print("  pipeline.fetch_historical_data('GOOGL', years=5, include_quarters=False)")


if __name__ == "__main__":
    main()