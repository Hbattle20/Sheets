# Balance Sheets Backend

A Python backend system for fetching and storing financial data from publicly traded companies. Built for the "Tinder for Balance Sheets" app where users guess if companies are undervalued based on their financial data.

## Features

- Fetches financial data from Financial Modeling Prep API
- Stores data in PostgreSQL (via Supabase)
- Calculates key financial ratios (P/E, P/B, ROE, etc.)
- Implements rate limiting and retry logic
- Tracks API usage to stay within limits

## Setup

1. **Clone the repository and install dependencies:**
```bash
cd balance-sheets-backend
pip install -r requirements.txt
```

    2. **Set up environment variables:**
    ```bash
    cp .env.example .env
    # Edit .env with your actual credentials
    ```

You'll need:
- Supabase project URL and API key
- Financial Modeling Prep API key (free tier available)

3. **Initialize the database:**
```bash
python setup.py
```

This will:
- Create all necessary database tables
- Test the connections
- Optionally fetch Microsoft (MSFT) data as a test

## Project Structure

```
balance-sheets-backend/
├── config.py          # Configuration and environment variables
├── database.py        # Database operations and connection management
├── fetcher.py         # Financial Modeling Prep API client
├── models.py          # Data models and SQL schemas
├── calculations.py    # Financial ratio calculations
├── pipeline.py        # Main ETL pipeline
├── setup.py          # Database initialization script
├── requirements.txt   # Python dependencies
└── .env.example      # Example environment variables
```

## Usage

### Fetch data for a company:
```python
from pipeline import DataPipeline

pipeline = DataPipeline()
pipeline.process_company('AAPL')  # Fetch Apple data
```

### Update market data only:
```python
pipeline.update_market_data('AAPL')  # Uses only 1 API call
```

### Check API usage:
```python
from database import Database

db = Database()
calls_today = db.get_api_calls_today()
print(f"API calls used today: {calls_today}/250")
```

## Database Schema

- **companies**: Basic company information
- **financial_snapshots**: Balance sheet and income statement data
- **market_data**: Current market cap and stock price
- **company_metrics**: Calculated financial ratios
- **data_fetch_log**: API call tracking

## API Limits

The free tier of Financial Modeling Prep allows:
- 250 API calls per day
- Each company fetch uses ~5 API calls
- Market data updates use 1 API call

## Financial Metrics Calculated

- **P/E Ratio**: Price to Earnings
- **P/B Ratio**: Price to Book Value
- **Debt/Equity**: Leverage ratio
- **ROE**: Return on Equity
- **Current Ratio**: Liquidity measure
- **Difficulty Score**: 1-10 rating for game purposes