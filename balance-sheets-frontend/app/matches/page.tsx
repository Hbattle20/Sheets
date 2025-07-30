'use client'

import { useState } from 'react'
import { useGameStore } from '@/stores/gameStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatCurrency } from '@/lib/utils'
import MatchDetail from '@/components/game/MatchDetail'

export default function MatchesPage() {
  const { savedMatches } = useGameStore()
  const [selectedMatchIndex, setSelectedMatchIndex] = useState<number | null>(null)

  if (selectedMatchIndex !== null && savedMatches[selectedMatchIndex]) {
    return (
      <main className="py-8">
        <div className="max-w-6xl mx-auto px-4">
          <button
            onClick={() => setSelectedMatchIndex(null)}
            className="mb-4 text-blue-600 hover:text-blue-800 flex items-center gap-2"
          >
            ← Back to Matches
          </button>
          <MatchDetail match={savedMatches[selectedMatchIndex]} />
        </div>
      </main>
    )
  }

  return (
    <main className="py-8">
      <div className="max-w-4xl mx-auto px-4">
        {savedMatches.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500 mb-4">No matches yet!</p>
              <p className="text-sm text-gray-400">
                Successfully guess a company's market cap to see it here.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {savedMatches.map((match, index) => (
              <Card 
                key={index} 
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setSelectedMatchIndex(index)}
              >
                <CardHeader>
                  <CardTitle className="text-lg">
                    {match.company.hiddenData.name}
                  </CardTitle>
                  <p className="text-sm text-gray-500">
                    {match.company.hiddenData.ticker} • {match.company.visibleData.sector}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-600">Your Guess:</span>{' '}
                      <span className="font-medium">{formatCurrency(match.guess)}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Actual:</span>{' '}
                      <span className="font-medium">{formatCurrency(match.actual)}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Difference:</span>{' '}
                      <span className={`font-medium ${match.percentageDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {match.percentageDiff >= 0 ? '+' : ''}{match.percentageDiff.toFixed(1)}%
                      </span>
                    </div>
                    <div className="pt-2 text-xs text-gray-400">
                      {new Date(match.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}