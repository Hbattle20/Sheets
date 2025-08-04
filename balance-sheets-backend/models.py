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


@dataclass
class UserMatch:
    """User's guess for a company's market cap"""
    id: Optional[int] = None
    user_id: str = ''  # UUID from auth.users
    company_id: int = 0
    guess: Decimal = Decimal('0')
    actual_market_cap: Decimal = Decimal('0')
    is_match: bool = False
    percentage_diff: Optional[Decimal] = None
    created_at: Optional[datetime] = None


@dataclass
class ChatSession:
    """Chat session between user and AI for a specific company"""
    id: Optional[int] = None
    user_id: str = ''  # UUID from auth.users
    company_id: int = 0
    created_at: Optional[datetime] = None


@dataclass
class ChatMessage:
    """Individual message in a chat session"""
    id: Optional[int] = None
    session_id: int = 0
    role: str = ''  # 'user' or 'assistant'
    content: str = ''
    created_at: Optional[datetime] = None


@dataclass
class AnnualReport:
    """Annual report (10-K) data"""
    id: Optional[int] = None
    company_id: int = 0
    fiscal_year: int = 0
    filing_date: Optional[datetime] = None
    
    # Key sections from 10-K
    business_overview: Optional[str] = None
    risk_factors: Optional[str] = None
    properties: Optional[str] = None
    legal_proceedings: Optional[str] = None
    md_and_a: Optional[str] = None  # Management Discussion & Analysis
    
    # Financial statement notes
    accounting_policies: Optional[str] = None
    revenue_recognition: Optional[str] = None
    segment_information: Optional[str] = None
    
    # Metadata
    filing_url: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


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

-- User matches table
CREATE TABLE IF NOT EXISTS user_matches (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    guess NUMERIC(20, 2),
    actual_market_cap NUMERIC(20, 2),
    is_match BOOLEAN,
    percentage_diff NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Annual reports table
CREATE TABLE IF NOT EXISTS annual_reports (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    filing_date DATE,
    
    -- Key sections from 10-K
    business_overview TEXT,
    risk_factors TEXT,
    properties TEXT,
    legal_proceedings TEXT,
    md_and_a TEXT,  -- Management Discussion & Analysis
    
    -- Financial statement notes
    accounting_policies TEXT,
    revenue_recognition TEXT,
    segment_information TEXT,
    
    -- Metadata
    filing_url TEXT,
    raw_json JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, fiscal_year)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_company_date ON financial_snapshots(company_id, period_end_date);
CREATE INDEX IF NOT EXISTS idx_market_data_last_updated ON market_data(last_updated);
CREATE INDEX IF NOT EXISTS idx_data_fetch_log_timestamp ON data_fetch_log(fetch_timestamp);
CREATE INDEX IF NOT EXISTS idx_user_matches_user_id ON user_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_annual_reports_company_year ON annual_reports(company_id, fiscal_year);
"""