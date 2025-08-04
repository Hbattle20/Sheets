"""Database operations for Balance Sheets Backend"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager

from config import SUPABASE_URL, SUPABASE_KEY, DATABASE_URL, DB_SCHEMA
from models import (
    Company, FinancialSnapshot, MarketData, 
    CompanyMetrics, DataFetchLog, AnnualReport, SQL_CREATE_TABLES
)

logger = logging.getLogger(__name__)


class Database:
    """Handle all database operations"""
    
    def __init__(self):
        # Use DATABASE_URL if provided, otherwise construct from components
        if DATABASE_URL:
            self.connection_string = DATABASE_URL
        else:
            # Parse Supabase URL to get connection parameters
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
            
            # Extract project reference from URL
            import re
            match = re.search(r'https://([^.]+)\.supabase\.co', SUPABASE_URL)
            if not match:
                raise ValueError("Invalid SUPABASE_URL format")
            
            project_ref = match.group(1)
            
            # Use direct connection format for more stability
            # Format: postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
            self.connection_string = f"postgresql://postgres:{SUPABASE_KEY}@db.{project_ref}.supabase.co:5432/postgres"
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with context manager"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_tables(self):
        """Create all database tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SQL_CREATE_TABLES)
                conn.commit()
                logger.info("Database tables created successfully")
    
    def insert_company(self, company: Company) -> int:
        """Insert or update a company and return its ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO companies (ticker, name, sector, industry, logo_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        logo_url = EXCLUDED.logo_url
                    RETURNING id
                """, (company.ticker, company.name, company.sector, 
                      company.industry, company.logo_url))
                
                result = cur.fetchone()
                conn.commit()
                return result['id']
    
    def insert_financial_snapshot(self, snapshot: FinancialSnapshot) -> int:
        """Insert a financial snapshot and return its ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO financial_snapshots 
                    (company_id, period_end_date, report_type, assets, liabilities, 
                     equity, cash, debt, revenue, net_income, operating_cash_flow,
                     free_cash_flow, shares_outstanding, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, period_end_date, report_type)
                    DO UPDATE SET
                        assets = EXCLUDED.assets,
                        liabilities = EXCLUDED.liabilities,
                        equity = EXCLUDED.equity,
                        cash = EXCLUDED.cash,
                        debt = EXCLUDED.debt,
                        revenue = EXCLUDED.revenue,
                        net_income = EXCLUDED.net_income,
                        operating_cash_flow = EXCLUDED.operating_cash_flow,
                        free_cash_flow = EXCLUDED.free_cash_flow,
                        shares_outstanding = EXCLUDED.shares_outstanding,
                        raw_data = EXCLUDED.raw_data
                    RETURNING id
                """, (
                    snapshot.company_id, snapshot.period_end_date, snapshot.report_type,
                    snapshot.assets, snapshot.liabilities, snapshot.equity,
                    snapshot.cash, snapshot.debt, snapshot.revenue,
                    snapshot.net_income, snapshot.operating_cash_flow,
                    snapshot.free_cash_flow, snapshot.shares_outstanding,
                    Json(snapshot.raw_data) if snapshot.raw_data else None
                ))
                
                result = cur.fetchone()
                conn.commit()
                return result['id']
    
    def update_market_data(self, market_data: MarketData):
        """Update or insert market data for a company"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO market_data (company_id, market_cap, stock_price, last_updated)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (company_id)
                    DO UPDATE SET
                        market_cap = EXCLUDED.market_cap,
                        stock_price = EXCLUDED.stock_price,
                        last_updated = EXCLUDED.last_updated
                """, (market_data.company_id, market_data.market_cap,
                      market_data.stock_price, market_data.last_updated))
                
                conn.commit()
    
    def insert_company_metrics(self, metrics: CompanyMetrics):
        """Insert or update company metrics"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO company_metrics 
                    (company_id, snapshot_id, p_e_ratio, p_b_ratio, debt_to_equity,
                     current_ratio, roe, difficulty_score, sector_percentile)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, snapshot_id)
                    DO UPDATE SET
                        p_e_ratio = EXCLUDED.p_e_ratio,
                        p_b_ratio = EXCLUDED.p_b_ratio,
                        debt_to_equity = EXCLUDED.debt_to_equity,
                        current_ratio = EXCLUDED.current_ratio,
                        roe = EXCLUDED.roe,
                        difficulty_score = EXCLUDED.difficulty_score,
                        sector_percentile = EXCLUDED.sector_percentile
                """, (
                    metrics.company_id, metrics.snapshot_id,
                    metrics.p_e_ratio, metrics.p_b_ratio, metrics.debt_to_equity,
                    metrics.current_ratio, metrics.roe,
                    metrics.difficulty_score, metrics.sector_percentile
                ))
                
                conn.commit()
    
    def log_fetch_attempt(self, log: DataFetchLog):
        """Log an API fetch attempt"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO data_fetch_log 
                    (ticker, fetch_timestamp, success, api_calls_used, error_message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (log.ticker, log.fetch_timestamp, log.success,
                      log.api_calls_used, log.error_message))
                
                conn.commit()
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company by ticker"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM companies WHERE ticker = %s
                """, (ticker,))
                
                return cur.fetchone()
    
    def get_latest_snapshot(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get the latest financial snapshot for a company"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM financial_snapshots 
                    WHERE company_id = %s
                    ORDER BY period_end_date DESC
                    LIMIT 1
                """, (company_id,))
                
                return cur.fetchone()
    
    def get_api_calls_today(self) -> int:
        """Get the number of API calls made today"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(api_calls_used), 0) as total_calls
                    FROM data_fetch_log
                    WHERE DATE(fetch_timestamp) = CURRENT_DATE
                    AND success = true
                """)
                
                result = cur.fetchone()
                return result[0] if result else 0
    
    def insert_or_update_annual_report(self, report: AnnualReport) -> int:
        """Insert or update an annual report
        
        Returns the report ID
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO annual_reports 
                    (company_id, fiscal_year, filing_date, business_overview,
                     risk_factors, properties, legal_proceedings, md_and_a,
                     accounting_policies, revenue_recognition, segment_information,
                     filing_url, raw_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, fiscal_year)
                    DO UPDATE SET
                        filing_date = EXCLUDED.filing_date,
                        business_overview = EXCLUDED.business_overview,
                        risk_factors = EXCLUDED.risk_factors,
                        properties = EXCLUDED.properties,
                        legal_proceedings = EXCLUDED.legal_proceedings,
                        md_and_a = EXCLUDED.md_and_a,
                        accounting_policies = EXCLUDED.accounting_policies,
                        revenue_recognition = EXCLUDED.revenue_recognition,
                        segment_information = EXCLUDED.segment_information,
                        filing_url = EXCLUDED.filing_url,
                        raw_json = EXCLUDED.raw_json
                    RETURNING id
                """, (
                    report.company_id, report.fiscal_year, report.filing_date,
                    report.business_overview, report.risk_factors, report.properties,
                    report.legal_proceedings, report.md_and_a,
                    report.accounting_policies, report.revenue_recognition,
                    report.segment_information, report.filing_url,
                    Json(report.raw_json) if report.raw_json else None
                ))
                
                result = cur.fetchone()
                conn.commit()
                return result['id']
    
    def get_annual_report(self, company_id: int, fiscal_year: int) -> Optional[Dict[str, Any]]:
        """Get an annual report for a company and year"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM annual_reports 
                    WHERE company_id = %s AND fiscal_year = %s
                """, (company_id, fiscal_year))
                
                return cur.fetchone()
    
    def get_latest_annual_report(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get the latest annual report for a company"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM annual_reports 
                    WHERE company_id = %s
                    ORDER BY fiscal_year DESC
                    LIMIT 1
                """, (company_id,))
                
                return cur.fetchone()
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False