'use client'

import { useEffect } from 'react'
import { animated, useSpring } from '@react-spring/web'
import { GameCompany } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { formatCurrency, isMatch, calculatePercentageDiff } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'

interface RevealAnimationProps {
  company: GameCompany
  guess: number
  onComplete: () => void
}

export default function RevealAnimation({ company, guess, onComplete }: RevealAnimationProps) {
  const { nextCompany } = useGameStore()
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
                Actual Market Cap: <span className="font-bold">
                  {formatCurrency(company.hiddenData.market_cap)}
                </span>
              </p>
              <p className="text-lg">
                Your Guess: <span className="font-bold">
                  {formatCurrency(guess)}
                </span>
              </p>
            </div>
          </div>

          <animated.div style={matchSpring} className="text-center">
            {match ? (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                <p className="text-2xl font-bold mb-1">MATCH! ✓</p>
                <p>You guessed {percentDiff >= 0 ? '+' : ''}{percentDiff.toFixed(1)}% 
                   {percentDiff >= 0 ? ' above' : ' below'} the actual market cap</p>
              </div>
            ) : (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <p className="text-2xl font-bold mb-1">NO MATCH ✗</p>
                <p>You guessed {percentDiff.toFixed(1)}% below the actual market cap</p>
              </div>
            )}
          </animated.div>

          <div className="text-center pt-4">
            <Button onClick={handleNext} size="lg">
              Next Company
            </Button>
          </div>
        </CardContent>
      </Card>
    </animated.div>
  )
}