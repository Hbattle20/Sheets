# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Tinder for Balance Sheets" - A full-stack guessing game where users estimate company market caps based on anonymized financial data. Players who guess at or above the actual market cap "match" with the company.

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
npm run dev     # Development server at localhost:3000
npm run build   # Production build
npm run lint    # ESLint checking
npm run type-check  # TypeScript checking
```

### Data Operations (Backend)
```bash
# Fetch current data for a company
python -c "from pipeline import DataPipeline; DataPipeline().process_company('AAPL')"

# Check API usage (250/day limit)
python -c "from database import Database; print(f'API calls: {Database().get_api_calls_today()}/250')"
```

## Database Schema (Supabase PostgreSQL)

### Core Tables
- **companies**: Basic company info (ticker, name, sector, logo)
- **financial_snapshots**: Balance sheet/income statement data
- **market_data**: Current market cap and stock price
- **company_metrics**: Calculated ratios (P/E, P/B, ROE, difficulty_score)
- **data_fetch_log**: API usage tracking

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

## Implementing Supabase Authentication

### 1. Database Setup for User Data

Create these tables in Supabase SQL editor:

```sql
-- User profiles (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    username TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- User game statistics
CREATE TABLE user_stats (
    user_id UUID REFERENCES profiles(id) PRIMARY KEY,
    total_guesses INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5,2) DEFAULT 0.00,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Individual guess history
CREATE TABLE guess_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    company_id INTEGER REFERENCES companies(id),
    market_cap_guess BIGINT NOT NULL,
    actual_market_cap BIGINT NOT NULL,
    is_match BOOLEAN NOT NULL,
    percentage_diff DECIMAL(10,2),
    guessed_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE guess_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own stats" ON user_stats
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own guess history" ON guess_history
    FOR SELECT USING (auth.uid() = user_id);

-- Trigger to create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id)
    VALUES (new.id);
    
    INSERT INTO public.user_stats (user_id)
    VALUES (new.id);
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 2. Frontend Authentication Implementation

#### Install Supabase Client
```bash
cd balance-sheets-frontend
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

#### Create Supabase Client (`lib/supabase.ts`)
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Type definitions for database
export type Profile = {
  id: string
  username: string | null
  created_at: string
  updated_at: string
}

export type UserStats = {
  user_id: string
  total_guesses: number
  total_matches: number
  current_streak: number
  best_streak: number
  accuracy_rate: number
}

export type GuessHistory = {
  id: number
  user_id: string
  company_id: number
  market_cap_guess: number
  actual_market_cap: number
  is_match: boolean
  percentage_diff: number
  guessed_at: string
}
```

#### Auth Context Provider (`components/auth/AuthProvider.tsx`)
```typescript
'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

type AuthContextType = {
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check active sessions and sets the user
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    // Listen for changes on auth state
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) throw error
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
```

#### Game Integration with Auth
```typescript
// In game component - track guesses for authenticated users
const submitGuess = async (marketCapGuess: number) => {
  const { user } = useAuth()
  
  // Calculate match
  const isMatch = marketCapGuess >= actualMarketCap
  
  if (user) {
    // Save to database
    const { error } = await supabase
      .from('guess_history')
      .insert({
        user_id: user.id,
        company_id: currentCompany.id,
        market_cap_guess: marketCapGuess,
        actual_market_cap: actualMarketCap,
        is_match: isMatch,
        percentage_diff: ((marketCapGuess - actualMarketCap) / actualMarketCap) * 100
      })
    
    // Update user stats
    await updateUserStats(user.id, isMatch)
  }
  
  // Continue with game logic...
}
```

### 3. Environment Variables

#### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=https://swzxvzamkqdtlbdadfxw.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

#### Backend (.env)
```
DATABASE_URL=postgresql://postgres.swzxvzamkqdtlbdadfxw:PASSWORD@aws-0-us-west-1.pooler.supabase.com:5432/postgres
FMP_API_KEY=your-fmp-api-key
```

### 4. Protected Routes & Middleware

Create `middleware.ts` in frontend root:
```typescript
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })

  const {
    data: { session },
  } = await supabase.auth.getSession()

  // Protected routes
  if (!session && req.nextUrl.pathname.startsWith('/profile')) {
    return NextResponse.redirect(new URL('/auth/login', req.url))
  }

  return res
}

export const config = {
  matcher: ['/profile/:path*', '/leaderboard/:path*']
}
```

### 5. User Features to Implement

1. **Profile Page** (`/profile`)
   - Display username, stats, match history
   - Edit profile settings
   - View achievement badges

2. **Leaderboard** (`/leaderboard`)
   - Global rankings by match rate
   - Weekly/monthly tournaments
   - Sector-specific leaderboards

3. **Social Features**
   - Share successful matches
   - Challenge friends
   - Follow top players

4. **Gamification**
   - Streak tracking
   - Achievement system
   - Difficulty progression

## API Rate Limits & Constraints

- Financial Modeling Prep: 250 calls/day (free tier)
- Each company fetch: ~5 API calls
- Currently loaded: MSFT, AAPL, GOOGL, AMZN, NVDA, META, TSLA, LLY, V, JPM, WMT, MA

## Performance Considerations

1. **Frontend**: Preload next cards, cache company data, lazy load images
2. **Backend**: Batch API calls, implement progress tracking for large imports
3. **Database**: Index on difficulty_score, use materialized views for complex queries

## Security Best Practices

1. **Never expose market cap** in initial API responses
2. **Validate all user inputs** on both client and server
3. **Use Row Level Security** for all user-specific data
4. **Rate limit guess submissions** to prevent gaming
5. **Sanitize financial data** before display

## Common Issues

1. **Supabase Connection**: Use Session pooler format, not direct connection
2. **TypeScript Errors**: Run `npm run type-check` before commits
3. **API Limits**: Monitor daily usage with `get_api_calls_today()`
4. **Auth State**: Always check loading state before rendering protected content