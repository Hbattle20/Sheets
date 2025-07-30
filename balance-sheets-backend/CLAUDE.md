# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python backend for the "Tinder for Balance Sheets" app that fetches and stores financial data from publicly traded companies using the Financial Modeling Prep API and PostgreSQL (via Supabase).

## Key Architecture Components

### Data Flow Architecture
1. **Financial Modeling Prep API** → Fetcher → Pipeline → Database → **Supabase PostgreSQL**
2. The system uses an ETL (Extract, Transform, Load) pattern with rate limiting and retry logic
3. Financial ratios are calculated on ingestion and stored for quick access

### Core Module Interactions
- `fetcher.py` (FMPClient) handles all API interactions with retry logic and rate limiting
- `pipeline.py` (DataPipeline) orchestrates the ETL process and manages the data flow
- `database.py` (Database) manages PostgreSQL connections using psycopg2 with connection pooling
- `calculations.py` (FinancialCalculator) computes financial ratios from raw data
- `models.py` defines data structures and contains the SQL schema (SQL_CREATE_TABLES)

### Database Connection Strategy
The system supports two connection methods:
1. Direct DATABASE_URL in .env (preferred)
2. Constructing from SUPABASE_URL + SUPABASE_KEY

Use the Session pooler connection format for Supabase:
```
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

## Essential Commands

### Setup and Installation
```bash
# Create and activate virtual environment
python3 -m venv balance-sheets-env
source balance-sheets-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (creates tables and optionally fetches test data)
python setup.py
```

### Data Fetching Operations
```python
# Fetch current data for a company (uses ~5 API calls)
from pipeline import DataPipeline
pipeline = DataPipeline()
pipeline.process_company('AAPL')

# Fetch historical data (uses ~30 API calls for 10 years annual)
from fetch_historical import HistoricalDataPipeline
pipeline = HistoricalDataPipeline()
pipeline.fetch_historical_data('MSFT', years=10, include_quarters=False)

# Update only market data (uses 1 API call)
pipeline.update_market_data('AAPL')
```

### Monitoring and Debugging
```bash
# Test database connection
python test_connection.py

# Check stored data
python check_data.py

# Check API usage
python -c "from database import Database; db = Database(); print(f'API calls today: {db.get_api_calls_today()}/250')"
```

## API Rate Limits and Data Constraints

- Free tier: 250 API calls/day
- Each company fetch: ~5 calls (profile, balance sheet, income, cash flow, quote, metrics)
- Historical data: 3 calls per period (balance, income, cash flow)
- Free tier returns only 5 years of historical data

## Environment Variables Required

```bash
# Supabase connection (use one of these approaches)
DATABASE_URL=postgresql://...  # Full connection string (preferred)
# OR
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_KEY=your-database-password  # NOT the anon key

# Financial Modeling Prep
FMP_API_KEY=your-api-key
```

## Database Schema Updates

When adding new fields to financial_snapshots:
1. Update the FinancialSnapshot dataclass in models.py
2. Update SQL_CREATE_TABLES in models.py
3. Update database.py insert_financial_snapshot method
4. Create and run a migration script (see add_cashflow_columns.py as example)

## Adding Multiple Companies at Scale

### Fetching All S&P 500 Companies
```python
# Create a batch processing script
from pipeline import DataPipeline
from fetch_historical import HistoricalDataPipeline
import time

# S&P 500 tickers list (abbreviated - get full list from a financial data source)
SP500_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'NVDA', ...]

pipeline = DataPipeline()
historical_pipeline = HistoricalDataPipeline()

for ticker in SP500_TICKERS:
    # Check daily API limit
    calls_today = pipeline.db.get_api_calls_today()
    if calls_today >= 240:  # Leave buffer
        print(f"Approaching daily limit ({calls_today}/250). Stopping for today.")
        break
    
    try:
        # Fetch current data first
        success = pipeline.process_company(ticker)
        if success:
            # Optionally fetch historical data (uses more API calls)
            # historical_pipeline.fetch_historical_data(ticker, years=5, include_quarters=False)
            time.sleep(1)  # Be respectful to the API
    except Exception as e:
        print(f"Failed to process {ticker}: {e}")
        continue
```

### Strategies for Large-Scale Data Collection

1. **Daily Batch Processing** (Free Tier)
   - ~50 companies/day with current data only
   - ~8 companies/day with 5 years of historical data
   - Create a scheduled job to run daily

2. **Prioritized Fetching**
   - Start with high market cap companies
   - Add sector diversity requirements
   - Track which companies need updates vs new additions

3. **Update Strategy**
   ```python
   # Update market data for existing companies (1 API call each)
   companies = db.get_all_companies()
   for company in companies:
       if calls_today < 240:
           pipeline.update_market_data(company['ticker'])
   ```

4. **Required Infrastructure for Scale**
   - Upgrade FMP API plan for higher limits
   - Implement a job scheduler (cron, Airflow, etc.)
   - Add error recovery and progress tracking
   - Consider caching unchanged data

## Common Issues and Solutions

1. **psycopg2 installation fails**: Use psycopg2-binary==2.9.10 for Python 3.13 support
2. **Database connection fails**: Ensure using database password, not Supabase anon key
3. **"Wrong password" errors**: Check if using Session pooler format with correct credentials
4. **API returns less historical data**: Free tier limitation - only returns 5 years
5. **Rate limit hit when batch processing**: Implement daily limits and progress tracking

## Frontend Integration Guide

### Key Data Available for the "Tinder for Balance Sheets" Game

#### Company Profile Data
```sql
-- Basic company info from 'companies' table
SELECT ticker, name, sector, industry, logo_url FROM companies;
```

#### Financial Snapshot Data (for displaying to users)
```sql
-- Get latest financial data for a company
SELECT 
    fs.*,
    c.name, c.sector, c.logo_url,
    md.market_cap, md.stock_price,
    cm.p_e_ratio, cm.p_b_ratio, cm.debt_to_equity, cm.roe, cm.difficulty_score
FROM companies c
JOIN financial_snapshots fs ON c.id = fs.company_id
JOIN market_data md ON c.id = md.company_id
JOIN company_metrics cm ON fs.id = cm.snapshot_id
WHERE c.ticker = 'AAPL'
ORDER BY fs.period_end_date DESC
LIMIT 1;
```

### Data Structure for Game Logic

1. **Anonymized Financial Display**
   - Hide: company name, ticker, identifying information
   - Show: sector, financial metrics, ratios
   - Use difficulty_score (1-10) to match with user skill level

2. **Key Metrics to Display**
   ```javascript
   const companyCard = {
     // Hidden until "match"
     hiddenData: {
       name: "Apple Inc.",
       ticker: "AAPL",
       logo_url: "https://..."
     },
     
     // Visible to user
     visibleData: {
       sector: "Technology",
       marketCap: 3500000000000,  // Show as "$3.5T"
       
       // Financial health indicators
       revenue: 394328000000,      // "$394.3B"
       netIncome: 99803000000,     // "$99.8B" 
       operatingCashFlow: 110563000000,  // "$110.6B"
       
       // Key ratios
       peRatio: 35.2,              // "35.2x"
       pbRatio: 49.8,              // "49.8x"
       debtToEquity: 1.95,         // "195%"
       roe: 147.3,                 // "147.3%"
       
       // Growth metrics (calculate from historical data)
       revenueGrowth: 0.08,        // "8% YoY"
       profitMargin: 0.253,        // "25.3%"
       
       difficultyScore: 7          // For matchmaking
     }
   };
   ```

3. **Valuation Game Logic**
   - User sees financial data (anonymized)
   - User guesses: "Undervalued" or "Fairly/Overvalued"
   - Reveal company name and actual market cap
   - "Match" if they correctly identified undervalued companies

### API Endpoints Needed

```python
# Suggested FastAPI/Flask endpoints for frontend

GET /api/companies/random?difficulty=5
# Returns anonymized company data for game

POST /api/guess
# Body: { company_id: 123, guess: "undervalued" }
# Returns: { correct: true, company_details: {...} }

GET /api/companies/{ticker}/history
# Returns historical data for charts

GET /api/leaderboard
# Returns top players by successful matches

GET /api/sectors
# Returns list of sectors for filtering
```

### Important Data Considerations

1. **Market Cap Ranges** (for difficulty scoring)
   - Mega cap: > $200B (easier to evaluate)
   - Large cap: $10B - $200B  
   - Mid cap: $2B - $10B
   - Small cap: < $2B (harder to evaluate)

2. **Sector-Specific Metrics**
   - Tech companies: High P/E ratios are normal
   - Banks: Focus on P/B ratio
   - Utilities: Dividend yield matters
   - Retail: Same-store sales growth

3. **Data Freshness**
   - market_data.last_updated: Real-time price data
   - financial_snapshots.period_end_date: Quarterly/annual reports
   - Flag if data is > 90 days old

4. **Calculating "Undervalued"**
   - Compare P/E to sector average
   - Compare P/B to historical average
   - Growth rate vs. P/E ratio (PEG ratio)
   - Store these calculations in company_metrics

### SQL Views for Frontend

```sql
-- Create a view for game-ready companies
CREATE VIEW game_companies AS
SELECT 
    c.id,
    c.sector,
    c.industry,
    fs.assets,
    fs.revenue,
    fs.net_income,
    fs.operating_cash_flow,
    md.market_cap,
    cm.p_e_ratio,
    cm.p_b_ratio,
    cm.debt_to_equity,
    cm.roe,
    cm.difficulty_score,
    md.last_updated
FROM companies c
JOIN financial_snapshots fs ON c.id = fs.company_id
JOIN market_data md ON c.id = md.company_id
JOIN company_metrics cm ON fs.id = cm.snapshot_id
WHERE fs.id IN (
    SELECT MAX(id) FROM financial_snapshots GROUP BY company_id
)
AND md.last_updated > NOW() - INTERVAL '7 days';
```

### Frontend Performance Tips

1. **Precompute expensive calculations** during data ingestion
2. **Cache sector averages** for comparison
3. **Use materialized views** for complex queries
4. **Index on difficulty_score** for quick game matching
5. **Batch fetch** related data to minimize API calls