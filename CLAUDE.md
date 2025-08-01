# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Buffett Sheets" (formerly "Tinder for Balance Sheets") - A full-stack financial guessing game where users estimate company market caps based on anonymized financial data. Players who guess at or above the actual market cap "match" with the company.

### Architecture
- **Backend** (`balance-sheets-backend/`): Python ETL pipeline fetching financial data from Financial Modeling Prep API → Supabase PostgreSQL
- **Frontend** (`balance-sheets-frontend/`): Next.js 15 + TypeScript + Tailwind CSS game interface with Zustand state management

## Essential Commands

### Backend Setup
```bash
cd balance-sheets-backend
python3 -m venv balance-sheets-env
source balance-sheets-env/bin/activate
pip install -r requirements.txt
python setup.py  # Initialize database tables
```

### Frontend Development
```bash
cd balance-sheets-frontend
npm install
npm run dev        # Development server at localhost:3000
npm run build      # Production build
npm run lint       # ESLint checking
```

### Data Operations (Backend)
```bash
# Fetch current data for a company
python -c "from pipeline import DataPipeline; DataPipeline().process_company('AAPL')"

# Check API usage (250/day limit)
python -c "from database import Database; print(f'API calls: {Database().get_api_calls_today()}/250')"

# Test database connection
python test_connection.py
```

## Code Architecture

### Backend Components
- `config.py`: Environment configuration and validation
- `database.py`: Supabase connection and CRUD operations
- `fetcher.py`: Financial Modeling Prep API client
- `models.py`: Data models with Pydantic validation
- `calculations.py`: Financial metrics (difficulty scores, ratios)
- `pipeline.py`: Main ETL orchestration

### Frontend Architecture
- **App Router** (`app/`): Next.js 15 pages with RSC support
- **Components** (`components/`): Modular UI components
  - `game/`: Core game UI (BalanceSheetCard, MarketCapSlider, ResultCard)
  - `auth/`: Authentication forms and profile components
  - `ui/`: Reusable UI primitives
- **State Management** (`stores/`): Zustand stores for game and user state
- **API Layer** (`lib/api.ts`): Centralized API client with type safety
- **Contexts**: AuthContext for user session management

### Key Frontend Components
- `BalanceSheetGame`: Main game orchestrator
- `BalanceSheetCard`: Displays anonymized financial data
- `MarketCapSlider`: Input UI for market cap guesses
- `ChatInterface`: AI-powered company analysis chat

## Database Schema (Supabase PostgreSQL)

### Core Tables
- **companies**: Basic company info (ticker, name, sector, logo)
- **financial_snapshots**: Balance sheet/income statement data
- **market_data**: Current market cap and stock price
- **company_metrics**: Calculated ratios (P/E, P/B, ROE, difficulty_score)
- **data_fetch_log**: API usage tracking

### User Tables
- **profiles**: User profiles linked to auth.users
- **user_stats**: Game statistics (matches, streaks, accuracy)
- **user_matches**: Individual guess history
- **chat_sessions/messages**: AI chat history

### Key Query for Game Data
```sql
SELECT 
    c.id, c.ticker, c.name, c.sector, c.logo_url,
    fs.revenue, fs.net_income, fs.operating_cash_flow,
    md.market_cap, md.stock_price,
    cm.p_e_ratio, cm.p_b_ratio, cm.debt_to_equity, cm.roe
FROM companies c
JOIN financial_snapshots fs ON c.id = fs.company_id
JOIN market_data md ON c.id = md.company_id
JOIN company_metrics cm ON fs.id = cm.snapshot_id
WHERE fs.period_end_date = (
    SELECT MAX(period_end_date) FROM financial_snapshots WHERE company_id = c.id
);
```

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://postgres.swzxvzamkqdtlbdadfxw:PASSWORD@aws-0-us-west-1.pooler.supabase.com:5432/postgres
FMP_API_KEY=your-fmp-api-key
SUPABASE_URL=https://swzxvzamkqdtlbdadfxw.supabase.co
SUPABASE_KEY=your-service-role-key
```

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=https://swzxvzamkqdtlbdadfxw.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

## API Rate Limits & Constraints

- Financial Modeling Prep: 250 calls/day (free tier)
- Each company fetch: ~5 API calls
- Currently loaded: MSFT, AAPL, GOOGL, AMZN, NVDA, META, TSLA, LLY, V, JPM, WMT, MA

## TypeScript Configuration

- Strict mode enabled
- Target: ES2017
- Module resolution: bundler
- Path aliases: `@/*` maps to project root

## Security Considerations

1. **Never expose market cap** in initial API responses
2. **Validate all user inputs** on both client and server
3. **Use Row Level Security** for all user-specific data
4. **Sanitize financial data** before display
5. **API keys**: Use service role key only in backend, anon key in frontend

## Common Development Patterns

### Adding New Companies
```python
# In backend
from pipeline import DataPipeline
pipeline = DataPipeline()
pipeline.process_company('NEW_TICKER')
```

### Fetching Game Data (Frontend)
```typescript
// Use the API client
import { api } from '@/lib/api'

const companies = await api.companies.getAll()
const nextCompany = await api.companies.getNext(excludeIds)
```

### Handling User Matches
```typescript
// Submit a guess
const result = await api.matches.submit({
  companyId,
  marketCapGuess,
  actualMarketCap,
  isMatch
})

// Update user stats automatically handled by database triggers
```

## Troubleshooting

1. **Database Connection**: Ensure using Supabase pooler URL format
2. **Auth Issues**: Check Supabase Auth settings and RLS policies
3. **API Limits**: Monitor with `get_api_calls_today()` method
4. **Type Errors**: Run `npm run lint` in frontend before commits