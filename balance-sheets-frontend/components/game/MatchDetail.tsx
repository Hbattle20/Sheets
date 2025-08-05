import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs } from '@/components/ui/Tabs'
import { BalanceSheet } from './BalanceSheet'
import { IncomeStatement } from './IncomeStatement'
import { CashFlowStatement } from './CashFlowStatement'
import { Chat } from './Chat'
import { formatCurrency } from '@/lib/utils'
import { getCompanyById } from '@/lib/api'
import { GameCompany } from '@/types'

interface MatchDetailProps {
  match: {
    company: any // GameCompany type
    guess: number
    actual: number
    percentageDiff: number
    timestamp: Date
  }
}

export default function MatchDetail({ match }: MatchDetailProps) {
  const [fullCompanyData, setFullCompanyData] = useState<GameCompany | null>(null)
  const [loading, setLoading] = useState(false)
  
  // Check if we already have historical data
  const hasHistoricalData = match.company.visibleData?.historicalData
  
  useEffect(() => {
    // If we don't have historical data, fetch the full company data
    if (!hasHistoricalData && match.company.id) {
      setLoading(true)
      getCompanyById(match.company.id)
        .then(data => {
          if (data) {
            setFullCompanyData(data)
          }
          setLoading(false)
        })
        .catch(() => {
          setLoading(false)
        })
    }
  }, [hasHistoricalData, match.company.id])
  
  // Use full company data if we fetched it, otherwise use the match data
  const companyData = fullCompanyData || match.company
  const historicalData = companyData.visibleData?.historicalData
  
  const tabs = historicalData ? [
    {
      id: 'balance-sheet',
      label: 'Balance Sheet',
      content: <BalanceSheet data={historicalData} />
    },
    {
      id: 'income-statement',
      label: 'Income Statement',
      content: <IncomeStatement data={historicalData} />
    },
    {
      id: 'cash-flow',
      label: 'Cash Flow',
      content: <CashFlowStatement data={historicalData} />
    }
  ] : []

  return (
    <Card className="max-w-6xl mx-auto">
      <CardHeader>
        <CardTitle className="text-2xl">
          {match.company.hiddenData.name}
        </CardTitle>
        <div className="flex items-center gap-4 mt-2">
          <span className="text-lg text-gray-600">{match.company.hiddenData.ticker}</span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            {match.company.visibleData.sector}
          </span>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-green-900 mb-2">Your Successful Match!</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Your Guess</p>
              <p className="font-bold text-lg">{formatCurrency(match.guess)}</p>
            </div>
            <div>
              <p className="text-gray-600">Actual Market Cap</p>
              <p className="font-bold text-lg">{formatCurrency(match.actual)}</p>
            </div>
            <div>
              <p className="text-gray-600">Difference</p>
              <p className={`font-bold text-lg ${match.percentageDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {match.percentageDiff >= 0 ? '+' : ''}{match.percentageDiff.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">Financial Statements</h3>
            {loading ? (
              <div className="bg-gray-50 rounded-lg p-4 text-gray-600 text-sm">
                <p>Loading financial data...</p>
              </div>
            ) : historicalData ? (
              <Tabs tabs={tabs} defaultTab="balance-sheet" />
            ) : (
              <div className="bg-gray-50 rounded-lg p-4 text-gray-600 text-sm">
                <p>Unable to load financial data for this company.</p>
                <p className="mt-2">Try refreshing the page or contact support if the issue persists.</p>
              </div>
            )}
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-4">Chat with Claude</h3>
            <Chat 
              companyName={match.company.hiddenData.name}
              companyId={match.company.id}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}