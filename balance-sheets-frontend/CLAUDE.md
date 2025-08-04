# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the frontend code for the "Tinder for Balance Sheets" app.

## Project Overview

A guessing game where users estimate the market cap of companies based on anonymized financial data. Users input their market cap guess, and if they guess at or above the actual market cap, they "match". The company identity is revealed after guessing, showing if they matched or not.

## Backend Data Available

The backend (balance-sheets-backend) stores financial data in Supabase PostgreSQL. Currently loaded companies include MSFT, AAPL, GOOGL, AMZN, NVDA, META, TSLA, LLY, V, JPM, WMT, MA.

### Key Tables and Data Structure

```sql
-- Get game-ready company data
SELECT 
    c.id, c.ticker, c.name, c.sector, c.industry, c.logo_url,
    fs.assets, fs.liabilities, fs.equity, fs.revenue, fs.net_income,
    fs.operating_cash_flow, fs.free_cash_flow,
    md.market_cap, md.stock_price,
    cm.p_e_ratio, cm.p_b_ratio, cm.debt_to_equity, cm.roe, cm.difficulty_score
FROM companies c
JOIN financial_snapshots fs ON c.id = fs.company_id
JOIN market_data md ON c.id = md.company_id  
JOIN company_metrics cm ON fs.id = cm.snapshot_id
WHERE fs.period_end_date = (
    SELECT MAX(period_end_date) FROM financial_snapshots WHERE company_id = c.id
);
```

### Data Fields for Game Display

**Hidden Until After Guess:**
- Company name
- Ticker symbol
- Logo URL
- Actual market cap

**Visible During Guessing:**
- Sector (e.g., "Technology", "Healthcare")
- Financial metrics:
  - Revenue: $X.XB (annual)
  - Net Income: $X.XB
  - Operating Cash Flow: $X.XB
  - Free Cash Flow: $X.XB
- Financial Ratios:
  - P/E Ratio: XX.X
  - P/B Ratio: XX.X
  - Debt/Equity: X.XX
  - ROE: XX.X%
- Difficulty Score: 1-10 (for matchmaking)

## Game Mechanics

### Core Flow
1. User sees anonymized financial data card
2. User inputs their market cap guess
3. Company identity revealed with animation
4. Show if they "matched" (guessed ≥ actual market cap)
5. Track score/matches

### Determining a "Match"
- User guesses the market cap
- If guess ≥ actual market cap: MATCH ✓
- If guess < actual market cap: NO MATCH ✗
- Show percentage difference to help users learn

### Difficulty Levels
- Beginner: Large cap, well-known metrics (difficulty 1-3)
- Intermediate: Mid cap, mixed signals (difficulty 4-7)  
- Expert: Small cap, complex financials (difficulty 8-10)

## Supabase Connection

### Option 1: Supabase Client SDK (Recommended)
```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://swzxvzamkqdtlbdadfxw.supabase.co'
const supabaseAnonKey = 'your-anon-key' // This is different from the database password

const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Fetch companies
const { data, error } = await supabase
  .from('companies')
  .select(`
    *,
    financial_snapshots!inner(*),
    market_data!inner(*),
    company_metrics!inner(*)
  `)
  .order('market_data.market_cap', { ascending: false })
```

### Option 2: Build API Layer
Create a simple API (FastAPI/Express) that connects to the database and provides endpoints:
- GET /api/companies/random?difficulty=5
- POST /api/guess { company_id, market_cap_guess }
- GET /api/matches
- GET /api/leaderboard

## UI/UX Considerations

### Card Design
```javascript
const CompanyCard = {
  // Visual hierarchy - NO MARKET CAP SHOWN
  primary: "Guess the Market Cap",
  
  // Key metrics grid
  metrics: {
    revenue: { label: "Revenue", value: "$245.1B", trend: "+8%" },
    profit: { label: "Net Income", value: "$88.1B", margin: "36%" },
    cashFlow: { label: "Free Cash Flow", value: "$74.1B" },
    pe: { label: "P/E Ratio", value: "43.2", status: "high" }
  },
  
  // Visual indicators
  sector: { icon: "💻", name: "Technology" },
  difficulty: { score: 6, color: "yellow" },
  
  // Guess input
  guessInput: { placeholder: "Enter market cap (e.g., 500B)", type: "text" }
}
```

### Guessing Interactions
- Market cap input field with formatting (B/T suffix support)
- Submit button or Enter key to confirm guess
- Reveal animation for company identity
- Match/no-match celebration or feedback animation
- Show actual vs guessed market cap comparison

### Progressive Disclosure
1. Start: Only key metrics visible (no market cap)
2. During guess: User inputs market cap estimate
3. After guess: Full company details + actual market cap + match result

## Recommended Tech Stack

### Framework Options
1. **Next.js + TypeScript** (Recommended)
   - Server-side rendering for SEO
   - API routes for backend
   - Great TypeScript support

2. **Vite + React**
   - Fast development
   - Lighter weight
   - Good for SPA

### Key Libraries
```json
{
  "dependencies": {
    "@supabase/supabase-js": "^2.x",
    "react": "^18.x",
    "react-spring": "^9.x",  // Card animations
    "react-hook-form": "^7.x",  // Form handling for guess input
    "recharts": "^2.x",  // Financial charts
    "tailwindcss": "^3.x",  // Styling
    "zustand": "^4.x"  // State management
  }
}
```

### Mobile Considerations
- Mobile-friendly number input
- Responsive card sizing
- PWA capabilities for app-like experience
- Haptic feedback on match
- Easy-to-use market cap input (with B/T shortcuts)

## Development Priorities

1. **MVP Features**
   - Market cap guessing interface
   - Company data display (excluding market cap)
   - Match/no-match logic (guess ≥ actual)
   - Score tracking

2. **Enhanced Features**
   - User accounts (Supabase Auth)
   - Leaderboards
   - Daily challenges
   - Educational tooltips

3. **Gamification**
   - Streaks for consecutive matches
   - Unlock new sectors/difficulties
   - Achievement badges
   - Weekly tournaments

## Data Formatting Helpers

```javascript
// Format large numbers
export const formatCurrency = (num: number): string => {
  if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`;
  if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`;
  return `$${num.toFixed(0)}`;
};

// Format ratios
export const formatRatio = (ratio: number, type: 'pe' | 'pb' | 'de'): string => {
  if (!ratio || ratio < 0) return 'N/A';
  if (type === 'de') return `${(ratio * 100).toFixed(0)}%`;
  return ratio.toFixed(1);
};

// Parse market cap guess (handles B/T suffixes)
export const parseMarketCapGuess = (input: string): number => {
  const cleaned = input.replace(/[$,\s]/g, '');
  const match = cleaned.match(/^(\d+(?:\.\d+)?)\s*([BTM])?$/i);
  if (!match) return 0;
  
  const num = parseFloat(match[1]);
  const suffix = match[2]?.toUpperCase();
  
  switch (suffix) {
    case 'T': return num * 1e12;
    case 'B': return num * 1e9;
    case 'M': return num * 1e6;
    default: return num;
  }
};

// Determine if it's a match
export const isMatch = (guess: number, actual: number): boolean => {
  return guess >= actual;
};
```

## Performance Optimization

1. **Preload next cards** while user is viewing current
2. **Cache company data** in localStorage/IndexedDB
3. **Lazy load** company logos and charts
4. **Validate** input before submission
5. **Use React.memo** for card components

## Testing Approach

```javascript
// Mock data for development
export const mockCompany = {
  id: 1,
  hiddenData: { name: "Apple Inc.", ticker: "AAPL", logo: "..." },
  visibleData: {
    sector: "Technology",
    marketCap: 3155486466000,
    revenue: 383285000000,
    netIncome: 96995000000,
    p_e_ratio: 33.66,
    p_b_ratio: 55.41,
    difficulty_score: 6
  }
};
```

## Common Pitfalls to Avoid

1. **Don't reveal company identity or market cap** in the initial data fetch
2. **Implement rate limiting** for guesses to prevent gaming
3. **Handle offline gracefully** with cached data
4. **Validate financial calculations** match backend
5. **Test on actual mobile devices** for input experience
6. **Prevent users from inspecting network requests** to see actual market cap

## Claude Chat Integration (Implemented)

### Overview
The chat feature is now fully integrated with Claude AI and provides contextual analysis based on actual 10-K filings stored in our vector database.

### Architecture
```
Frontend Chat UI → Next.js API Route (/api/chat) → Vector Database (Supabase pgvector) → Claude API
```

### Data Available
- **5 years of Microsoft 10-K filings** (2021-2025) processed into 329 searchable chunks
- **3072-dimensional embeddings** using OpenAI's text-embedding-3-large model
- **All standard 10-K sections** including Business, Risk Factors, MD&A, Financial Statements

### API Endpoint: `/app/api/chat/route.ts`
The endpoint:
1. Receives user message and company context
2. Generates embedding for the question using OpenAI
3. Searches relevant 10-K chunks using vector similarity (top 20 chunks)
4. Falls back to keyword search if needed
5. Sends context + question to Claude 3.5 Sonnet
6. Returns informed analysis based on actual filings

### Environment Variables Required
```bash
# In .env.local (server-side only, no NEXT_PUBLIC prefix)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...  # For embedding generation
```

### Example Queries That Work Well
- "How has Microsoft's cloud revenue grown over the past 5 years?"
- "What are the main cybersecurity risks Microsoft faces?"
- "Compare Microsoft's R&D spending trends from 2021 to 2025"
- "What acquisitions has Microsoft made recently?"
- "Analyze Microsoft's debt-to-equity ratio changes"

### Current Limitations
- Only Microsoft data loaded (can add more companies)
- 10-K annual reports only (can add 10-Q quarterly reports)
- No real-time data (only up to filing dates)

### Future Enhancements
1. **Add more companies**: Process S&P 500 companies
2. **Add 10-Q reports**: Quarterly updates for more recent data
3. **Add 8-K filings**: Major events and earnings announcements
4. **Improve chunking**: Better handling of tables and financial data
5. **Add streaming**: Stream Claude's responses for better UX