"""Financial Modeling Prep API client"""
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from decimal import Decimal

from config import (
    FMP_API_KEY, FMP_BASE_URL, FMP_RETRY_ATTEMPTS, 
    FMP_RETRY_DELAY, FMP_RATE_LIMIT_PER_DAY
)

logger = logging.getLogger(__name__)


class FMPClient:
    """Client for Financial Modeling Prep API"""
    
    def __init__(self):
        self.api_key = FMP_API_KEY
        self.base_url = FMP_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Balance-Sheets-Backend/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the FMP API with retry logic"""
        if params is None:
            params = {}
        
        params['apikey'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(FMP_RETRY_ATTEMPTS):
            try:
                logger.info(f"Making request to {endpoint} (attempt {attempt + 1})")
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if isinstance(data, dict) and 'Error Message' in data:
                    raise Exception(f"API Error: {data['Error Message']}")
                
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{FMP_RETRY_ATTEMPTS}): {e}")
                
                if attempt < FMP_RETRY_ATTEMPTS - 1:
                    wait_time = FMP_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Get company profile information"""
        data = self._make_request(f"profile/{ticker}")
        return data[0] if data else {}
    
    def get_balance_sheet(self, ticker: str, period: str = 'annual', limit: int = 1) -> List[Dict[str, Any]]:
        """Get balance sheet data
        
        Args:
            ticker: Stock ticker symbol
            period: 'annual' for 10-K or 'quarter' for 10-Q
            limit: Number of periods to fetch
        """
        return self._make_request(
            f"balance-sheet-statement/{ticker}",
            params={'period': period, 'limit': limit}
        )
    
    def get_income_statement(self, ticker: str, period: str = 'annual', limit: int = 1) -> List[Dict[str, Any]]:
        """Get income statement data
        
        Args:
            ticker: Stock ticker symbol
            period: 'annual' for 10-K or 'quarter' for 10-Q
            limit: Number of periods to fetch
        """
        return self._make_request(
            f"income-statement/{ticker}",
            params={'period': period, 'limit': limit}
        )
    
    def get_cash_flow_statement(self, ticker: str, period: str = 'annual', limit: int = 1) -> List[Dict[str, Any]]:
        """Get cash flow statement data
        
        Args:
            ticker: Stock ticker symbol
            period: 'annual' for 10-K or 'quarter' for 10-Q
            limit: Number of periods to fetch
        """
        return self._make_request(
            f"cash-flow-statement/{ticker}",
            params={'period': period, 'limit': limit}
        )
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote with market cap and price"""
        data = self._make_request(f"quote/{ticker}")
        return data[0] if data else {}
    
    def get_key_metrics(self, ticker: str, period: str = 'annual', limit: int = 1) -> List[Dict[str, Any]]:
        """Get key financial metrics"""
        return self._make_request(
            f"key-metrics/{ticker}",
            params={'period': period, 'limit': limit}
        )
    
    def get_sec_filings(self, ticker: str, filing_type: str = '10-K', limit: int = 5) -> List[Dict[str, Any]]:
        """Get SEC filings list for a company
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.)
            limit: Number of filings to return
        """
        return self._make_request(
            f"v3/sec_filings/{ticker}",
            params={'type': filing_type, 'page': 0}
        )[:limit]
    
    def get_financial_reports_json(self, ticker: str, year: int, period: str = 'FY') -> Dict[str, Any]:
        """Get parsed financial report data (10-K or 10-Q)
        
        Args:
            ticker: Stock ticker symbol
            year: Fiscal year
            period: 'FY' for annual (10-K) or 'Q1', 'Q2', 'Q3', 'Q4' for quarterly
        """
        return self._make_request(
            f"v4/financial-reports-json",
            params={'symbol': ticker, 'year': year, 'period': period}
        )
    
    def fetch_annual_report(self, ticker: str, year: Optional[int] = None) -> Dict[str, Any]:
        """Fetch annual report (10-K) data for a company
        
        Returns a dictionary with:
        - filing_info: Basic filing information
        - sections: Parsed 10-K sections if available
        - success: Whether fetch was successful
        - api_calls_used: Number of API calls made
        """
        api_calls = 0
        result = {
            'success': False,
            'api_calls_used': 0
        }
        
        try:
            # First, get the filing information
            logger.info(f"Fetching 10-K filings list for {ticker}")
            filings = self.get_sec_filings(ticker, '10-K', 5)
            api_calls += 1
            
            if not filings:
                raise Exception("No 10-K filings found")
            
            # Find the filing for the requested year or get the latest
            target_filing = None
            if year:
                for filing in filings:
                    filing_year = int(filing.get('fillingDate', '')[:4])
                    if filing_year == year or filing_year == year + 1:  # Filed in year or early next year
                        target_filing = filing
                        break
            else:
                target_filing = filings[0]  # Latest filing
            
            if not target_filing:
                raise Exception(f"No 10-K filing found for year {year}")
            
            result['filing_info'] = {
                'filing_date': target_filing.get('fillingDate'),
                'accepted_date': target_filing.get('acceptedDate'),
                'filing_url': target_filing.get('link'),
                'final_url': target_filing.get('finalLink')
            }
            
            # Extract year from filing
            filing_year = int(target_filing.get('fillingDate', '')[:4])
            fiscal_year = filing_year - 1  # Usually for previous fiscal year
            
            # Try to get parsed report data
            logger.info(f"Fetching parsed 10-K data for {ticker} fiscal year {fiscal_year}")
            try:
                report_data = self.get_financial_reports_json(ticker, fiscal_year, 'FY')
                api_calls += 1
                
                if report_data:
                    result['sections'] = report_data
                    result['has_parsed_data'] = True
            except Exception as e:
                logger.warning(f"Could not fetch parsed report data: {e}")
                result['has_parsed_data'] = False
            
            result['fiscal_year'] = fiscal_year
            result['api_calls_used'] = api_calls
            result['success'] = True
            
            logger.info(f"Successfully fetched 10-K data for {ticker} using {api_calls} API calls")
            
        except Exception as e:
            logger.error(f"Error fetching 10-K for {ticker}: {e}")
            result['error'] = str(e)
            result['api_calls_used'] = api_calls
        
        return result
    
    def fetch_company_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch all necessary data for a company
        
        Returns a dictionary with:
        - profile: Company profile data
        - balance_sheet: Latest balance sheet
        - income_statement: Latest income statement
        - quote: Current market data
        - metrics: Key financial metrics
        - api_calls_used: Number of API calls made
        """
        api_calls = 0
        result = {}
        
        try:
            # Get company profile
            logger.info(f"Fetching company profile for {ticker}")
            result['profile'] = self.get_company_profile(ticker)
            api_calls += 1
            
            # Get latest annual balance sheet
            logger.info(f"Fetching balance sheet for {ticker}")
            balance_sheets = self.get_balance_sheet(ticker, 'annual', 1)
            result['balance_sheet'] = balance_sheets[0] if balance_sheets else {}
            api_calls += 1
            
            # Get latest annual income statement
            logger.info(f"Fetching income statement for {ticker}")
            income_statements = self.get_income_statement(ticker, 'annual', 1)
            result['income_statement'] = income_statements[0] if income_statements else {}
            api_calls += 1
            
            # Get current quote with market cap
            logger.info(f"Fetching quote for {ticker}")
            result['quote'] = self.get_quote(ticker)
            api_calls += 1
            
            # Get key metrics
            logger.info(f"Fetching key metrics for {ticker}")
            metrics = self.get_key_metrics(ticker, 'annual', 1)
            result['metrics'] = metrics[0] if metrics else {}
            api_calls += 1
            
            result['api_calls_used'] = api_calls
            result['success'] = True
            
            logger.info(f"Successfully fetched all data for {ticker} using {api_calls} API calls")
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            result['api_calls_used'] = api_calls
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def parse_financial_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and clean financial data from API response
        
        Extracts relevant fields and converts to appropriate types
        """
        parsed = {}
        
        # Parse company profile
        if profile := data.get('profile', {}):
            parsed['company'] = {
                'ticker': profile.get('symbol', ''),
                'name': profile.get('companyName', ''),
                'sector': profile.get('sector'),
                'industry': profile.get('industry'),
                'logo_url': profile.get('image')
            }
        
        # Parse balance sheet
        if bs := data.get('balance_sheet', {}):
            parsed['balance_sheet'] = {
                'period_end_date': bs.get('date'),
                'report_type': '10-K' if bs.get('period') == 'FY' else '10-Q',
                'assets': Decimal(str(bs.get('totalAssets', 0))),
                'liabilities': Decimal(str(bs.get('totalLiabilities', 0))),
                'equity': Decimal(str(bs.get('totalStockholdersEquity', 0))),
                'cash': Decimal(str(bs.get('cashAndCashEquivalents', 0))),
                'debt': Decimal(str(bs.get('totalDebt', 0)))
            }
        
        # Parse income statement
        if income := data.get('income_statement', {}):
            parsed['income_statement'] = {
                'revenue': Decimal(str(income.get('revenue', 0))),
                'net_income': Decimal(str(income.get('netIncome', 0)))
            }
        
        # Parse quote/market data
        if quote := data.get('quote', {}):
            parsed['market_data'] = {
                'market_cap': Decimal(str(quote.get('marketCap', 0))),
                'stock_price': Decimal(str(quote.get('price', 0))),
                'shares_outstanding': Decimal(str(quote.get('sharesOutstanding', 0)))
            }
        
        # Parse key metrics
        if metrics := data.get('metrics', {}):
            parsed['metrics'] = {
                'p_e_ratio': Decimal(str(metrics.get('peRatio', 0))) if metrics.get('peRatio') else None,
                'p_b_ratio': Decimal(str(metrics.get('pbRatio', 0))) if metrics.get('pbRatio') else None,
                'debt_to_equity': Decimal(str(metrics.get('debtToEquity', 0))) if metrics.get('debtToEquity') else None,
                'current_ratio': Decimal(str(metrics.get('currentRatio', 0))) if metrics.get('currentRatio') else None,
                'roe': Decimal(str(metrics.get('roe', 0))) if metrics.get('roe') else None
            }
        
        return parsed