'use client'

import { useEffect } from 'react'
import { useGameStore } from '@/stores/gameStore'
import { getRandomCompany } from '@/lib/api'
import CompanyCard from '@/components/game/CompanyCard'
import ScoreBoard from '@/components/game/ScoreBoard'

export default function Home() {
  const { currentCompany, setCurrentCompany, isRevealing } = useGameStore()

  useEffect(() => {
    if (!currentCompany && !isRevealing) {
      loadNewCompany()
    }
  }, [currentCompany, isRevealing])

  const loadNewCompany = async () => {
    const company = await getRandomCompany()
    if (company) {
      setCurrentCompany(company)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Buffett Sheets
          </h1>
          <p className="text-lg text-gray-600">
            Guess the market cap based on financial data
          </p>
        </header>

        <div>
          {currentCompany ? (
            <CompanyCard company={currentCompany} />
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading company data...</p>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}