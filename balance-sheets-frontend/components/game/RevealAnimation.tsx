'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { animated, useSpring } from '@react-spring/web'
import { GameCompany } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Tabs } from '@/components/ui/Tabs'
import { BalanceSheet } from './BalanceSheet'
import { IncomeStatement } from './IncomeStatement'
import { CashFlowStatement } from './CashFlowStatement'
import { formatCurrency, isMatch, calculatePercentageDiff } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'

interface RevealAnimationProps {
  company: GameCompany
  guess: number
  onComplete: () => void
}

export default function RevealAnimation({ company, guess, onComplete }: RevealAnimationProps) {
  const { nextCompany } = useGameStore()
  const router = useRouter()
  const [showFinancials, setShowFinancials] = useState(false)
  const match = isMatch(guess, company.hiddenData.market_cap)
  const percentDiff = calculatePercentageDiff(guess, company.hiddenData.market_cap)

  const revealSpring = useSpring({
    from: { opacity: 0, transform: 'scale(0.8)' },
    to: { opacity: 1, transform: 'scale(1)' },
    config: { tension: 300, friction: 20 }
  })

  const matchSpring = useSpring({
    from: { opacity: 0, y: 20 },
    to: { opacity: 1, y: 0 },
    delay: 300,
    config: { tension: 200, friction: 20 }
  })

  const handleNext = () => {
    nextCompany()
    onComplete()
  }

  const financialTabs = [
    {
      id: 'balance-sheet',
      label: 'Balance Sheet',
      mobileLabel: 'Balance',
      content: <BalanceSheet data={company.visibleData.historicalData} />
    },
    {
      id: 'income-statement',
      label: 'Income Statement',
      mobileLabel: 'Income',
      content: <IncomeStatement data={company.visibleData.historicalData} />
    },
    {
      id: 'cash-flow',
      label: 'Cash Flow',
      mobileLabel: 'Cash Flow',
      content: <CashFlowStatement data={company.visibleData.historicalData} />
    }
  ]

  return (
    <animated.div style={revealSpring}>
      <Card className="max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <CardTitle>Company Revealed!</CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold mb-2">{company.hiddenData.name}</h2>
            <p className="text-xl text-gray-600 mb-4">{company.hiddenData.ticker}</p>
            
            <div className="space-y-2">
              <p className="text-lg">
                Actual Company Value: <span className="font-bold">
                  {formatCurrency(company.hiddenData.market_cap)}
                </span>
              </p>
              <p className="text-lg">
                Your Estimate: <span className="font-bold">
                  {formatCurrency(guess)}
                </span>
              </p>
            </div>
          </div>

          <animated.div style={matchSpring} className="text-center">
            {match ? (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                <p className="text-2xl font-bold mb-1">MATCH! ✓</p>
                <p>Your estimate is {percentDiff >= 0 ? '+' : ''}{percentDiff.toFixed(1)}% 
                   {percentDiff >= 0 ? ' above' : ' below'} the actual value</p>
              </div>
            ) : (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <p className="text-2xl font-bold mb-1">NO MATCH ✗</p>
                <p>Your estimate is {percentDiff.toFixed(1)}% below the actual value</p>
              </div>
            )}
          </animated.div>

          <div className="flex flex-col items-center gap-3 pt-4">
            <div className="flex gap-3">
              <Button onClick={handleNext} size="lg">
                Next Company
              </Button>
              <Button 
                onClick={() => router.push('/matches')} 
                size="lg"
                variant="outline"
              >
                Matches
              </Button>
            </div>
            <Button 
              onClick={() => setShowFinancials(!showFinancials)} 
              variant="outline"
              size="sm"
            >
              {showFinancials ? 'Hide' : 'Review'} Financials
            </Button>
          </div>
        </CardContent>
      </Card>

      {showFinancials && (
        <animated.div style={matchSpring} className="mt-4">
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="text-lg">Financial Statements</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs tabs={financialTabs} defaultTab="balance-sheet" />
            </CardContent>
          </Card>
        </animated.div>
      )}
    </animated.div>
  )
}