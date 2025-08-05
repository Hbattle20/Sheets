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

## Claude Chat Integration Plan

The chat feature currently uses mock responses. Here's the step-by-step plan to integrate real Claude API:

### Current Implementation
- **Frontend**: `components/game/Chat.tsx` - Working UI with mock responses
- **Database**: `chat_sessions` and `chat_messages` tables with RLS policies
- **Mock Service**: `lib/chatService.ts` - Returns placeholder responses

### Step 1: Create Backend API Endpoint
Create a Next.js API route to handle chat requests:

```typescript
// app/api/chat/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import Anthropic from '@anthropic-ai/sdk'

export async function POST(request: NextRequest) {
  // 1. Authenticate user
  // 2. Get message and company ID from request
  // 3. Fetch company financial data from Supabase
  // 4. Call Claude API with context
  // 5. Save response to database
  // 6. Return response
}
```

### Step 2: Install and Configure Anthropic SDK
```bash
cd balance-sheets-frontend
npm install @anthropic-ai/sdk
```

Add to `.env.local`:
```
ANTHROPIC_API_KEY=your-api-key-here
```

### Step 3: Implement Context Injection
Fetch and format company data for Claude:

```typescript
async function getCompanyContext(companyId: number) {
  // Fetch from Supabase:
  // - Company info (name, sector)
  // - Historical financials (10 years)
  // - Current metrics (P/E, P/B, ROE)
  // - Market data
  
  return {
    company: { name, sector, ticker },
    financials: historicalData,
    metrics: currentMetrics,
    marketCap: currentMarketCap
  }
}
```

### Step 4: Create Claude System Prompt
```typescript
const SYSTEM_PROMPT = `You are a financial analyst helping users understand company financials. 
You have access to 10 years of financial data including balance sheets, income statements, 
and cash flow statements. Provide insightful analysis about trends, ratios, and financial health.
Be concise but thorough. If you notice concerning trends, mention them objectively.`
```

### Step 5: Update Chat Component
Replace the mock implementation in `Chat.tsx`:

```typescript
// Instead of setTimeout mock:
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage.content,
    companyId,
    sessionId
  })
})
const data = await response.json()
```

### Step 6: Error Handling & Rate Limiting
- Handle API errors gracefully
- Implement rate limiting per user
- Add retry logic for transient failures
- Stream responses for better UX (optional)

### Step 7: Testing & Monitoring
- Test with various financial questions
- Monitor API usage and costs
- Log errors for debugging
- Add analytics for popular questions

### Implementation Order
1. **First**: Create basic API endpoint with mock response
2. **Second**: Add Anthropic SDK and test Claude integration
3. **Third**: Implement company data fetching and context
4. **Fourth**: Update frontend to use real API
5. **Fifth**: Add error handling and rate limiting
6. **Sixth**: Optimize with streaming and caching

## Production Deployment Readiness

### 🚨 Critical Blockers (Must Fix Before Deployment)

✅ ~~Security Headers Added~~
✅ ~~Test Route Removed~~

**All critical blockers have been resolved!**

### 🔴 Backend Issues (Data Collection Only - Not Production Critical)

Since the backend is only used for data collection and doesn't serve the frontend, these are non-blocking issues:
- Missing some dependencies in `requirements.txt` for auxiliary scripts
- No connection pooling (acceptable for batch ETL operations)
- Rate limiting configured for premium tier (750/min)

### 🟡 Frontend Issues

**Code Quality:**
- ✅ ~~Console.log statements removed~~
- 7 instances of TypeScript `any` types
- No error boundaries for React component crashes
- Zero test coverage

**Production Readiness:**
- Missing loading.tsx and error.tsx pages
- No 404 page
- No robots.txt, sitemap.xml, or favicon
- No SEO metadata configuration
- No performance optimizations (lazy loading, code splitting)

**Security:**
- No input validation on API routes
- Service role key usage in frontend code
- Missing rate limiting on all endpoints
- No API route authentication middleware

### 🟠 Database Issues

**Schema Problems:**
- Missing tables mentioned in docs: `profiles`, `user_stats`
- Missing critical indexes for performance
- No connection pooling implementation
- Missing NOT NULL constraints on required fields

**Required Indexes:**
```sql
CREATE INDEX idx_financial_snapshots_company_report ON financial_snapshots(company_id, report_type);
CREATE INDEX idx_company_metrics_company ON company_metrics(company_id);
CREATE INDEX idx_user_matches_user_created ON user_matches(user_id, created_at DESC);
CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at);
```

### 📋 Pre-Deployment Checklist

#### Immediate Security Fixes:
- [ ] Rotate all exposed API keys
- [ ] Remove .env files from git history
- [ ] Remove /test-supabase route
- [ ] Add security headers to next.config.js
- [ ] Implement input validation on all API routes

#### Backend Fixes:
- [ ] Update requirements.txt with all dependencies
- [ ] Implement database connection pooling
- [ ] Add request timeouts (30s recommended)
- [ ] Fix bare exception handlers
- [ ] Add transaction support for multi-table operations

#### Frontend Fixes:
- [ ] Remove all console.log statements
- [ ] Fix TypeScript any types
- [ ] Add error boundaries
- [ ] Create error.tsx and not-found.tsx pages
- [ ] Add robots.txt and favicon
- [ ] Implement proper loading states

#### Database Fixes:
- [ ] Create missing tables (profiles, user_stats)
- [ ] Add required indexes
- [ ] Implement connection pooling
- [ ] Add data validation constraints

### Production Environment Setup

#### Required Environment Variables:
```bash
# Backend
DATABASE_URL=postgresql://[connection-string]
FMP_API_KEY=[your-key]
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=[service-role-key]  # Backend only!

# Frontend
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[anon-key]
ANTHROPIC_API_KEY=[your-key]  # Server-side only
```

#### Recommended next.config.js:
```javascript
const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-XSS-Protection', value: '1; mode=block' },
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
  { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' }
]

module.exports = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  async headers() {
    return [{
      source: '/:path*',
      headers: securityHeaders,
    }]
  }
}
```

### Deployment Readiness Score: 3/10

The application has solid architecture but requires significant security and production hardening before deployment. Priority should be given to:
1. Removing exposed API keys
2. Adding security headers
3. Removing test routes
4. Implementing proper error handling
5. Adding missing database tables and indexes

### Post-Deployment Monitoring

Once deployed, implement:
- Error tracking (Sentry)
- Performance monitoring (Vercel Analytics)
- API usage monitoring
- Database query performance tracking
- Uptime monitoring for external API dependencies