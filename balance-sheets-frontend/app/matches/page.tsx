'use client'

import { useState, useEffect } from 'react'
import { useGameStore } from '@/stores/gameStore'
import { useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatCurrency } from '@/lib/utils'
import MatchDetail from '@/components/game/MatchDetail'

interface DatabaseMatch {
  id: number
  user_id: string
  company_id: number
  guess: number
  actual_market_cap: number
  is_match: boolean
  percentage_diff: number
  created_at: string
  company: {
    id: number
    name: string
    ticker: string
    sector: string
    logo_url: string
  }
}

export default function MatchesPage() {
  const { savedMatches: localMatches } = useGameStore()
  const { user } = useAuth()
  const [matches, setMatches] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedMatchIndex, setSelectedMatchIndex] = useState<number | null>(null)

  useEffect(() => {
    const loadMatches = async () => {
      if (user) {
        // Load from database for authenticated users
        try {
          const { data, error } = await supabase
            .from('user_matches')
            .select(`
              *,
              company:companies(
                id,
                name,
                ticker,
                sector,
                logo_url
              )
            `)
            .eq('user_id', user.id)
            .order('created_at', { ascending: false })

          if (error) {
            console.error('Error loading matches:', error)
            // Fall back to local storage on error
            setMatches(localMatches)
          } else {
            // Transform database matches to match local format
            const transformedMatches = data.map((match: DatabaseMatch) => ({
              company: {
                id: match.company.id,
                hiddenData: {
                  name: match.company.name,
                  ticker: match.company.ticker,
                  market_cap: match.actual_market_cap,
                  logo: match.company.logo_url
                },
                visibleData: {
                  sector: match.company.sector,
                  // Note: historicalData not available from database
                  historicalData: null
                }
              },
              guess: match.guess,
              actual: match.actual_market_cap,
              isMatch: match.is_match,
              percentageDiff: match.percentage_diff,
              timestamp: new Date(match.created_at),
              fromDatabase: true // Flag to indicate limited data
            }))
            setMatches(transformedMatches)
          }
        } catch (error) {
          console.error('Error loading matches:', error)
          setMatches(localMatches)
        }
      } else {
        // Use local storage for anonymous users
        setMatches(localMatches)
      }
      setLoading(false)
    }

    loadMatches()
  }, [user, localMatches])

  if (selectedMatchIndex !== null && matches[selectedMatchIndex]) {
    return (
      <main className="py-8">
        <div className="max-w-6xl mx-auto px-4">
          <button
            onClick={() => setSelectedMatchIndex(null)}
            className="mb-4 text-blue-600 hover:text-blue-800 flex items-center gap-2"
          >
            ← Back to Matches
          </button>
          <MatchDetail match={matches[selectedMatchIndex]} />
        </div>
      </main>
    )
  }

  return (
    <main className="py-8">
      <div className="max-w-4xl mx-auto px-4">
        {loading ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">Loading matches...</p>
            </CardContent>
          </Card>
        ) : matches.length === 0 ? (
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
            {matches.map((match, index) => (
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