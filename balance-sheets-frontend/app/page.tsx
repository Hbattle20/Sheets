'use client'

import { useEffect } from 'react'
import { useGameStore } from '@/stores/gameStore'
import { getRandomCompany } from '@/lib/api'
import CompanyCard from '@/components/game/CompanyCard'
import { FeedbackButton } from '@/components/ui/FeedbackButton'

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
    <main className="py-8">
      <div className="max-w-4xl mx-auto px-4">
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