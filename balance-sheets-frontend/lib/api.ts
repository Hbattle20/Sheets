import { supabase } from './supabase'
import { GameCompany } from '@/types'

async function fetchCompanyData(company: any): Promise<GameCompany | null> {
  try {
    // Get all financial snapshots for this company (for historical data)
    const { data: allSnapshots, error: snapshotError } = await supabase
      .from('financial_snapshots')
      .select('*')
      .eq('company_id', company.id)
      .eq('report_type', '10-K') // Annual reports only
      .order('period_end_date', { ascending: false })

    if (snapshotError || !allSnapshots || allSnapshots.length === 0) {
      console.error('Error fetching snapshots:', snapshotError)
      return null
    }

    const latestSnapshot = allSnapshots[0]

    // Get market data
    const { data: marketData, error: marketError } = await supabase
      .from('market_data')
      .select('*')
      .eq('company_id', company.id)
      .single()

    if (marketError || !marketData) {
      console.error('Error fetching market data:', marketError)
      return null
    }

    // Get company metrics for this snapshot
    const { data: metrics, error: metricsError } = await supabase
      .from('company_metrics')
      .select('*')
      .eq('company_id', company.id)
      .eq('snapshot_id', latestSnapshot.id)
      .single()

    if (metricsError || !metrics) {
      console.error('Error fetching metrics:', metricsError)
      return null
    }

    // Build 10 years of historical data
    const currentYear = new Date().getFullYear()
    const historicalData = []
    
    for (let i = 0; i < 10; i++) {
      const targetYear = currentYear - i
      const snapshot = allSnapshots.find(s => 
        new Date(s.period_end_date).getFullYear() === targetYear
      )
      
      historicalData.push({
        year: targetYear,
        // Balance Sheet
        assets: snapshot?.assets || 0,
        liabilities: snapshot?.liabilities || 0,
        equity: snapshot?.equity || 0,
        cash: snapshot?.cash || 0,
        debt: snapshot?.debt || 0,
        // Income Statement
        revenue: snapshot?.revenue || 0,
        net_income: snapshot?.net_income || 0,
        // Cash Flow
        operating_cash_flow: snapshot?.operating_cash_flow || 0,
        free_cash_flow: snapshot?.free_cash_flow || 0,
        shares_outstanding: snapshot?.shares_outstanding || 0,
      })
    }

    console.log('Built historical data:', historicalData)

    // Transform the data to match our GameCompany interface
    const gameCompany: GameCompany = {
      id: company.id,
      hiddenData: {
        name: company.name,
        ticker: company.ticker,
        logo_url: company.logo_url || '',
        market_cap: marketData.market_cap,
      },
      visibleData: {
        sector: company.sector,
        industry: company.industry,
        historicalData,
        currentMetrics: {
          p_e_ratio: metrics.p_e_ratio,
          p_b_ratio: metrics.p_b_ratio,
          debt_to_equity: metrics.debt_to_equity,
          roe: metrics.roe,
          difficulty_score: metrics.difficulty_score,
        },
      },
    }

    return gameCompany
  } catch (error) {
    console.error('Error fetching company data:', error)
    return null
  }
}

export async function getCompanyById(companyId: number): Promise<GameCompany | null> {
  try {
    // Get the specific company
    const { data: company, error: companyError } = await supabase
      .from('companies')
      .select('*')
      .eq('id', companyId)
      .single()
    
    if (companyError || !company) {
      console.error('Error fetching company:', companyError)
      return null
    }

    return await fetchCompanyData(company)
  } catch (error) {
    console.error('Error in getCompanyById:', error)
    return null
  }
}

export async function getRandomCompany(difficulty?: number): Promise<GameCompany | null> {
  try {
    // First, get all companies
    const { data: companies, error: companiesError } = await supabase
      .from('companies')
      .select('*')
    
    if (companiesError || !companies || companies.length === 0) {
      console.error('Error fetching companies:', companiesError)
      return null
    }

    // Select a random company
    const randomCompany = companies[Math.floor(Math.random() * companies.length)]

    const gameCompany = await fetchCompanyData(randomCompany)
    
    if (!gameCompany) {
      return null
    }

    // Apply difficulty filter if provided
    if (difficulty && Math.abs(gameCompany.visibleData.currentMetrics.difficulty_score - difficulty) > 1) {
      // Try again with a different company
      return getRandomCompany(difficulty)
    }

    return gameCompany
  } catch (error) {
    console.error('Error in getRandomCompany:', error)
    return null
  }
}