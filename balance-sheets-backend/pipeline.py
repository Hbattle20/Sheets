"""ETL Pipeline for fetching and storing financial data"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from config import FMP_RATE_LIMIT_PER_DAY
from database import Database
from fetcher import FMPClient
from calculations import FinancialCalculator
from models import (
    Company, FinancialSnapshot, MarketData,
    CompanyMetrics, DataFetchLog, AnnualReport
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPipeline:
    """Main ETL pipeline for financial data"""
    
    def __init__(self):
        self.db = Database()
        self.api_client = FMPClient()
    
    def check_rate_limit(self) -> bool:
        """Check if we're within API rate limits"""
        calls_today = self.db.get_api_calls_today()
        
        if calls_today >= FMP_RATE_LIMIT_PER_DAY:
            logger.warning(f"Rate limit reached: {calls_today}/{FMP_RATE_LIMIT_PER_DAY} calls today")
            return False
        
        logger.info(f"API calls today: {calls_today}/{FMP_RATE_LIMIT_PER_DAY}")
        return True
    
    def process_company(self, ticker: str) -> bool:
        """Process a single company - fetch data, calculate metrics, and store
        
        Returns True if successful, False otherwise
        """
        logger.info(f"Starting to process {ticker}")
        
        # Check rate limit
        if not self.check_rate_limit():
            logger.error("Rate limit exceeded, cannot process company")
            return False
        
        # Initialize fetch log
        fetch_log = DataFetchLog(
            ticker=ticker,
            fetch_timestamp=datetime.now()
        )
        
        try:
            # Fetch all data from API
            logger.info(f"Fetching data from Financial Modeling Prep API for {ticker}")
            raw_data = self.api_client.fetch_company_data(ticker)
            
            fetch_log.api_calls_used = raw_data.get('api_calls_used', 0)
            
            if not raw_data.get('success', False):
                raise Exception(raw_data.get('error', 'Unknown error'))
            
            # Parse the data
            parsed_data = FMPClient.parse_financial_data(raw_data)
            
            # Store company information
            company_data = parsed_data.get('company', {})
            company = Company(
                ticker=company_data.get('ticker'),
                name=company_data.get('name'),
                sector=company_data.get('sector'),
                industry=company_data.get('industry'),
                logo_url=company_data.get('logo_url')
            )
            
            logger.info(f"Inserting company: {company.name}")
            company_id = self.db.insert_company(company)
            
            # Store financial snapshot
            bs_data = parsed_data.get('balance_sheet', {})
            income_data = parsed_data.get('income_statement', {})
            market_data = parsed_data.get('market_data', {})
            
            snapshot = FinancialSnapshot(
                company_id=company_id,
                period_end_date=datetime.strptime(bs_data.get('period_end_date'), '%Y-%m-%d'),
                report_type=bs_data.get('report_type', '10-K'),
                assets=bs_data.get('assets'),
                liabilities=bs_data.get('liabilities'),
                equity=bs_data.get('equity'),
                cash=bs_data.get('cash'),
                debt=bs_data.get('debt'),
                revenue=income_data.get('revenue'),
                net_income=income_data.get('net_income'),
                shares_outstanding=market_data.get('shares_outstanding'),
                raw_data=raw_data  # Store complete API response
            )
            
            logger.info(f"Inserting financial snapshot for period ending {snapshot.period_end_date}")
            snapshot_id = self.db.insert_financial_snapshot(snapshot)
            
            # Update market data
            market = MarketData(
                company_id=company_id,
                market_cap=market_data.get('market_cap'),
                stock_price=market_data.get('stock_price'),
                last_updated=datetime.now()
            )
            
            logger.info(f"Updating market data - Market Cap: ${market.market_cap:,.0f}")
            self.db.update_market_data(market)
            
            # Calculate financial metrics
            logger.info("Calculating financial metrics")
            metrics_data = FinancialCalculator.calculate_all_metrics(
                stock_price=market.stock_price,
                market_cap=market.market_cap,
                net_income=snapshot.net_income,
                shares_outstanding=snapshot.shares_outstanding,
                assets=snapshot.assets,
                liabilities=snapshot.liabilities,
                equity=snapshot.equity,
                debt=snapshot.debt
            )
            
            # Store metrics
            metrics = CompanyMetrics(
                company_id=company_id,
                snapshot_id=snapshot_id,
                p_e_ratio=metrics_data.get('p_e_ratio'),
                p_b_ratio=metrics_data.get('p_b_ratio'),
                debt_to_equity=metrics_data.get('debt_to_equity'),
                current_ratio=metrics_data.get('current_ratio'),
                roe=metrics_data.get('roe'),
                difficulty_score=metrics_data.get('difficulty_score')
            )
            
            logger.info(f"Storing calculated metrics - P/E: {metrics.p_e_ratio}, P/B: {metrics.p_b_ratio}")
            self.db.insert_company_metrics(metrics)
            
            # Success!
            fetch_log.success = True
            logger.info(f"Successfully processed {ticker}")
            
            # Print summary
            self._print_summary(ticker, company, snapshot, market, metrics)
            
            # Try to fetch annual report (optional, don't fail if it doesn't work)
            try:
                self.fetch_and_store_annual_report(ticker, company_id)
            except Exception as e:
                logger.warning(f"Could not fetch annual report for {ticker}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            fetch_log.success = False
            fetch_log.error_message = str(e)
            return False
            
        finally:
            # Always log the fetch attempt
            self.db.log_fetch_attempt(fetch_log)
    
    def _print_summary(self, ticker: str, company: Company, snapshot: FinancialSnapshot,
                      market: MarketData, metrics: CompanyMetrics):
        """Print a summary of what was stored"""
        print(f"\n{'='*50}")
        print(f"Successfully stored data for {ticker}")
        print(f"{'='*50}")
        print(f"\nCompany: {company.name}")
        print(f"Sector: {company.sector}")
        print(f"Industry: {company.industry}")
        print(f"\nFinancial Data (Period: {snapshot.period_end_date}):")
        print(f"  Assets: ${snapshot.assets:,.0f}")
        print(f"  Liabilities: ${snapshot.liabilities:,.0f}")
        print(f"  Equity: ${snapshot.equity:,.0f}")
        print(f"  Revenue: ${snapshot.revenue:,.0f}")
        print(f"  Net Income: ${snapshot.net_income:,.0f}")
        print(f"\nMarket Data:")
        print(f"  Market Cap: ${market.market_cap:,.0f}")
        print(f"  Stock Price: ${market.stock_price:.2f}")
        print(f"\nCalculated Metrics:")
        print(f"  P/E Ratio: {metrics.p_e_ratio or 'N/A'}")
        print(f"  P/B Ratio: {metrics.p_b_ratio or 'N/A'}")
        print(f"  Debt/Equity: {metrics.debt_to_equity or 'N/A'}")
        print(f"  ROE: {metrics.roe or 'N/A'}%")
        print(f"  Difficulty Score: {metrics.difficulty_score}/10")
        print(f"{'='*50}\n")
    
    def update_market_data(self, ticker: str) -> bool:
        """Update only market data for a company (uses fewer API calls)"""
        logger.info(f"Updating market data for {ticker}")
        
        # Get company from database
        company = self.db.get_company_by_ticker(ticker)
        if not company:
            logger.error(f"Company {ticker} not found in database")
            return False
        
        # Check rate limit
        if not self.check_rate_limit():
            return False
        
        fetch_log = DataFetchLog(
            ticker=ticker,
            fetch_timestamp=datetime.now(),
            api_calls_used=1
        )
        
        try:
            # Fetch only quote data
            quote = self.api_client.get_quote(ticker)
            
            if not quote:
                raise Exception("No quote data returned")
            
            # Update market data
            market = MarketData(
                company_id=company['id'],
                market_cap=quote.get('marketCap', 0),
                stock_price=quote.get('price', 0),
                last_updated=datetime.now()
            )
            
            self.db.update_market_data(market)
            
            fetch_log.success = True
            logger.info(f"Successfully updated market data for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating market data for {ticker}: {e}")
            fetch_log.success = False
            fetch_log.error_message = str(e)
            return False
            
        finally:
            self.db.log_fetch_attempt(fetch_log)
    
    def fetch_and_store_annual_report(self, ticker: str, company_id: int, year: Optional[int] = None) -> bool:
        """Fetch and store annual report (10-K) data
        
        Args:
            ticker: Company ticker symbol
            company_id: Database ID of the company
            year: Specific year to fetch (optional, defaults to latest)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Fetching annual report for {ticker} (year: {year or 'latest'})")
        
        try:
            # Fetch 10-K data from FMP
            report_data = self.api_client.fetch_annual_report(ticker, year)
            
            if not report_data.get('success'):
                logger.error(f"Failed to fetch annual report: {report_data.get('error')}")
                return False
            
            # Extract sections from the response
            fiscal_year = report_data.get('fiscal_year')
            filing_info = report_data.get('filing_info', {})
            sections = report_data.get('sections', {})
            
            # Parse filing date
            filing_date = None
            if filing_date_str := filing_info.get('filing_date'):
                try:
                    filing_date = datetime.strptime(filing_date_str[:10], '%Y-%m-%d')
                except:
                    pass
            
            # Create AnnualReport object
            annual_report = AnnualReport(
                company_id=company_id,
                fiscal_year=fiscal_year,
                filing_date=filing_date,
                filing_url=filing_info.get('filing_url'),
                raw_json=sections  # Store the entire response for future use
            )
            
            # Try to extract specific sections if available
            if isinstance(sections, dict):
                # These field names will depend on what FMP actually returns
                # We'll need to adjust based on the test results
                annual_report.business_overview = self._extract_text(sections, ['business', 'businessDescription', 'item1'])
                annual_report.risk_factors = self._extract_text(sections, ['riskFactors', 'risks', 'item1a'])
                annual_report.properties = self._extract_text(sections, ['properties', 'item2'])
                annual_report.legal_proceedings = self._extract_text(sections, ['legalProceedings', 'legal', 'item3'])
                annual_report.md_and_a = self._extract_text(sections, ['mdna', 'mdAndA', 'managementDiscussion', 'item7'])
                annual_report.accounting_policies = self._extract_text(sections, ['accountingPolicies', 'significantAccountingPolicies'])
                annual_report.revenue_recognition = self._extract_text(sections, ['revenueRecognition'])
                annual_report.segment_information = self._extract_text(sections, ['segments', 'operatingSegments'])
            
            # Store in database
            report_id = self.db.insert_or_update_annual_report(annual_report)
            logger.info(f"Successfully stored annual report for {ticker} (fiscal year {fiscal_year}, ID: {report_id})")
            
            # Log the API calls used
            if api_calls := report_data.get('api_calls_used', 0):
                fetch_log = DataFetchLog(
                    ticker=ticker,
                    fetch_timestamp=datetime.now(),
                    success=True,
                    api_calls_used=api_calls,
                    error_message=f"Annual report fetch for fiscal year {fiscal_year}"
                )
                self.db.log_fetch_attempt(fetch_log)
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching annual report for {ticker}: {e}")
            return False
    
    def _extract_text(self, data: Dict[str, Any], possible_keys: List[str], max_length: Optional[int] = None) -> Optional[str]:
        """Extract text from data using possible field names
        
        Args:
            data: Dictionary to search in
            possible_keys: List of possible field names to try
            max_length: Maximum length of text to store (optional)
            
        Returns:
            The extracted text or None
        """
        for key in possible_keys:
            if value := data.get(key):
                if isinstance(value, str):
                    text = value.strip()
                    if max_length and len(text) > max_length:
                        text = text[:max_length] + "..."
                    return text
                elif isinstance(value, dict):
                    # Recursively search in nested dict
                    if text := self._extract_text(value, ['text', 'content', 'value']):
                        return text
        return None