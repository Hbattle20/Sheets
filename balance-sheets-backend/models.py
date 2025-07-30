"""Data models for Balance Sheets Backend"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


@dataclass
class Company:
    """Company basic information"""
    id: Optional[int] = None
    ticker: str = ''
    name: str = ''
    sector: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class FinancialSnapshot:
    """Financial statement data for a specific period"""
    id: Optional[int] = None
    company_id: int = 0
    period_end_date: datetime = None
    report_type: str = ''  # 10-K or 10-Q
    
    # Balance Sheet Items
    assets: Decimal = Decimal('0')
    liabilities: Decimal = Decimal('0')
    equity: Decimal = Decimal('0')
    cash: Decimal = Decimal('0')
    debt: Decimal = Decimal('0')
    
    # Income Statement Items
    revenue: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')
    
    # Cash Flow Items
    operating_cash_flow: Decimal = Decimal('0')
    free_cash_flow: Decimal = Decimal('0')
    
    # Other
    shares_outstanding: Decimal = Decimal('0')
    raw_data: Dict[str, Any] = None  # Store complete API response


@dataclass
class MarketData:
    """Current market data for a company"""
    company_id: int
    market_cap: Decimal
    stock_price: Decimal
    last_updated: datetime


@dataclass
class CompanyMetrics:
    """Pre-calculated metrics for the game"""
    company_id: int
    snapshot_id: int
    
    # Financial Ratios
    p_e_ratio: Optional[Decimal] = None
    p_b_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    roe: Optional[Decimal] = None  # Return on Equity
    
    # Game-specific
    difficulty_score: int = 5  # 1-10
    sector_percentile: Optional[int] = None  # 1-100


@dataclass
class DataFetchLog:
    """Log of API fetch attempts"""
    id: Optional[int] = None
    ticker: str = ''
    fetch_timestamp: datetime = None
    success: bool = False
    api_calls_used: int = 0
    error_message: Optional[str] = None


# SQL Table Creation Statements
SQL_CREATE_TABLES = """
-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    logo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Financial snapshots table
CREATE TABLE IF NOT EXISTS financial_snapshots (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    period_end_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL CHECK (report_type IN ('10-K', '10-Q')),
    
    -- Balance Sheet
    assets NUMERIC(20, 2),
    liabilities NUMERIC(20, 2),
    equity NUMERIC(20, 2),
    cash NUMERIC(20, 2),
    debt NUMERIC(20, 2),
    
    -- Income Statement
    revenue NUMERIC(20, 2),
    net_income NUMERIC(20, 2),
    
    -- Cash Flow Statement
    operating_cash_flow NUMERIC(20, 2),
    free_cash_flow NUMERIC(20, 2),
    
    -- Other
    shares_outstanding NUMERIC(20, 2),
    raw_data JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, period_end_date, report_type)
);

-- Market data table
CREATE TABLE IF NOT EXISTS market_data (
    company_id INTEGER PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
    market_cap NUMERIC(20, 2) NOT NULL,
    stock_price NUMERIC(10, 2) NOT NULL,
    last_updated TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Company metrics table
CREATE TABLE IF NOT EXISTS company_metrics (
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    snapshot_id INTEGER REFERENCES financial_snapshots(id) ON DELETE CASCADE,
    
    -- Ratios
    p_e_ratio NUMERIC(10, 2),
    p_b_ratio NUMERIC(10, 2),
    debt_to_equity NUMERIC(10, 2),
    current_ratio NUMERIC(10, 2),
    roe NUMERIC(10, 2),
    
    -- Game metrics
    difficulty_score INTEGER CHECK (difficulty_score >= 1 AND difficulty_score <= 10),
    sector_percentile INTEGER CHECK (sector_percentile >= 1 AND sector_percentile <= 100),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, snapshot_id)
);

-- Data fetch log table
CREATE TABLE IF NOT EXISTS data_fetch_log (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    fetch_timestamp TIMESTAMP NOT NULL,
    success BOOLEAN NOT NULL,
    api_calls_used INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_company_date ON financial_snapshots(company_id, period_end_date);
CREATE INDEX IF NOT EXISTS idx_market_data_last_updated ON market_data(last_updated);
CREATE INDEX IF NOT EXISTS idx_data_fetch_log_timestamp ON data_fetch_log(fetch_timestamp);
"""