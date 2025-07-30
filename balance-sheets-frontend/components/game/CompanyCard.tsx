'use client'

import { useState } from 'react'
import { GameCompany } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs } from '@/components/ui/Tabs'
import { BalanceSheet } from './BalanceSheet'
import { IncomeStatement } from './IncomeStatement'
import { CashFlowStatement } from './CashFlowStatement'
import GuessInput from './GuessInput'
import RevealAnimation from './RevealAnimation'
import { useGameStore } from '@/stores/gameStore'

interface CompanyCardProps {
  company: GameCompany
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const { isRevealing, lastGuess } = useGameStore()
  const [hasGuessed, setHasGuessed] = useState(false)

  const handleGuessSubmit = () => {
    setHasGuessed(true)
  }

  if (isRevealing && hasGuessed && lastGuess) {
    return (
      <RevealAnimation
        company={company}
        guess={lastGuess}
        onComplete={() => setHasGuessed(false)}
      />
    )
  }

  const tabs = [
    {
      id: 'balance-sheet',
      label: 'Balance Sheet',
      content: <BalanceSheet data={company.visibleData.historicalData} />
    },
    {
      id: 'income-statement',
      label: 'Income Statement',
      content: <IncomeStatement data={company.visibleData.historicalData} />
    },
    {
      id: 'cash-flow',
      label: 'Cash Flow',
      content: <CashFlowStatement data={company.visibleData.historicalData} />
    }
  ]

  return (
    <Card className="max-w-6xl mx-auto">
      <CardHeader>
        <CardTitle className="text-center">Guess the Market Cap</CardTitle>
        <div className="flex items-center justify-center mt-2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            {company.visibleData.sector}
          </span>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="mb-6">
          <Tabs tabs={tabs} defaultTab="balance-sheet" />
        </div>
        
        <div className="mt-6 pt-6 border-t">
          <GuessInput onSubmit={handleGuessSubmit} />
        </div>
      </CardContent>
    </Card>
  )
}