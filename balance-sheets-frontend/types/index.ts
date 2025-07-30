export interface Company {
  id: number
  ticker: string
  name: string
  sector: string
  industry: string
  logo_url: string
}

export interface FinancialSnapshot {
  id: number
  company_id: number
  period_end_date: string
  assets: number
  liabilities: number
  equity: number
  revenue: number
  net_income: number
  operating_cash_flow: number
  free_cash_flow: number
}

export interface MarketData {
  id: number
  company_id: number
  market_cap: number
  stock_price: number
  date: string
}

export interface CompanyMetrics {
  id: number
  snapshot_id: number
  p_e_ratio: number
  p_b_ratio: number
  debt_to_equity: number
  roe: number
  difficulty_score: number
}

export interface HistoricalFinancials {
  year: number
  // Balance Sheet
  assets: number
  liabilities: number
  equity: number
  cash: number
  debt: number
  // Income Statement
  revenue: number
  net_income: number
  // Cash Flow
  operating_cash_flow: number
  free_cash_flow: number
  shares_outstanding: number
}

export interface GameCompany {
  id: number
  hiddenData: {
    name: string
    ticker: string
    logo_url: string
    market_cap: number
  }
  visibleData: {
    sector: string
    industry: string
    historicalData: HistoricalFinancials[]
    currentMetrics: {
      p_e_ratio: number
      p_b_ratio: number
      debt_to_equity: number
      roe: number
      difficulty_score: number
    }
  }
}

export interface GameState {
  currentCompany: GameCompany | null
  score: number
  matches: number
  totalGuesses: number
  streak: number
  isRevealing: boolean
  lastGuess: number | null
  guessHistory: GuessResult[]
}

export interface GuessResult {
  companyId: number
  companyName: string
  guess: number
  actual: number
  isMatch: boolean
  percentageDiff: number
  timestamp: Date
}