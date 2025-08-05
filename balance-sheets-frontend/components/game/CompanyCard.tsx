'use client'

import { useState, useEffect } from 'react'
import { GameCompany } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs } from '@/components/ui/Tabs'
import { BalanceSheet } from './BalanceSheet'
import { IncomeStatement } from './IncomeStatement'
import { CashFlowStatement } from './CashFlowStatement'
import GuessInput from './GuessInput'
import RevealAnimation from './RevealAnimation'
import { MatchAuthPrompt } from './MatchAuthPrompt'
import { AuthModal } from '@/components/auth/AuthModal'
import { useGameStore } from '@/stores/gameStore'
import { useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'

interface CompanyCardProps {
  company: GameCompany
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const { isRevealing, lastGuess } = useGameStore()
  const { user } = useAuth()
  const [hasGuessed, setHasGuessed] = useState(false)
  const [showMatchPrompt, setShowMatchPrompt] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authModalView, setAuthModalView] = useState<'signin' | 'signup'>('signup')
  const [waitingForAuth, setWaitingForAuth] = useState(false)
  const [previousUser, setPreviousUser] = useState(user)
  const [pendingMatch, setPendingMatch] = useState<{
    companyId: number
    guess: number
    actualMarketCap: number
  } | null>(null)

  // Check for pending match on mount
  useEffect(() => {
    const savedPendingMatch = localStorage.getItem('pendingMatch')
    if (savedPendingMatch) {
      try {
        const match = JSON.parse(savedPendingMatch)
        setPendingMatch(match)
      } catch (e) {
        // Error parsing pending match
      }
    }
  }, [])

  // Watch for authentication changes when waiting
  useEffect(() => {
    
    // Check if user just signed in (was null, now has value)
    if (!previousUser && user && (waitingForAuth || pendingMatch)) {
      
      // User just authenticated, save the match to database
      const saveMatch = async () => {
        // Use pending match data if available, otherwise use current state
        const matchData = pendingMatch || (lastGuess && company ? {
          companyId: company.id,
          guess: lastGuess,
          actualMarketCap: company.hiddenData.market_cap
        } : null)
        
        if (matchData) {
          const isMatch = matchData.guess >= matchData.actualMarketCap
          
          // Only save if it was actually a match
          if (!isMatch) {
            return
          }
          
          try {
            const { error } = await supabase
              .from('user_matches')
              .insert({
                user_id: user.id,
                company_id: matchData.companyId,
                guess: matchData.guess,
                actual_market_cap: matchData.actualMarketCap,
                is_match: isMatch,
                percentage_diff: ((matchData.guess - matchData.actualMarketCap) / matchData.actualMarketCap) * 100,
              })
              
            if (!error) {
              // Clear from localStorage after successful save
              localStorage.removeItem('pendingMatch')
            }
          } catch (error) {
            // Error saving match after authentication
          }
        }
      }
      
      saveMatch()
      
      // Clear pending match and proceed with reveal
      setPendingMatch(null)
      setWaitingForAuth(false)
      setShowAuthModal(false)
    }
    
    // Update previous user for next render
    if (user !== previousUser) {
      setPreviousUser(user)
    }
  }, [user, waitingForAuth, lastGuess, company, previousUser, pendingMatch])

  const handleGuessSubmit = () => {
    setHasGuessed(true)
    
    // We'll check for match after the guess is processed
    setTimeout(() => {
      const store = useGameStore.getState()
      const currentGuess = store.lastGuess
      
      // Check if it's a match and user is not authenticated
      if (currentGuess && currentGuess >= company.hiddenData.market_cap && !user) {
        // Save match data for later
        const matchData = {
          companyId: company.id,
          guess: currentGuess,
          actualMarketCap: company.hiddenData.market_cap
        }
        setPendingMatch(matchData)
        
        // Also save to localStorage in case user needs to confirm email
        localStorage.setItem('pendingMatch', JSON.stringify(matchData))
        
        setShowMatchPrompt(true)
      }
    }, 100)
  }

  const handleSignUp = () => {
    setShowMatchPrompt(false)
    setAuthModalView('signup')
    setShowAuthModal(true)
    setWaitingForAuth(true)
  }

  const handleSignIn = () => {
    setShowMatchPrompt(false)
    setAuthModalView('signin')
    setShowAuthModal(true)
    setWaitingForAuth(true)
  }

  const handleMaybeLater = () => {
    setShowMatchPrompt(false)
    setWaitingForAuth(false)
    // Continue with normal reveal for anonymous users
  }

  // Show reveal animation for authenticated users or after "maybe later"
  if (isRevealing && hasGuessed && lastGuess && !showMatchPrompt && !waitingForAuth) {
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
    <>
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

      <MatchAuthPrompt
        isOpen={showMatchPrompt}
        onSignUp={handleSignUp}
        onSignIn={handleSignIn}
        onMaybeLater={handleMaybeLater}
      />

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => {
          setShowAuthModal(false)
          // If user closed modal without authenticating, stop waiting
          setTimeout(() => {
            if (waitingForAuth && !user) {
              setWaitingForAuth(false)
            }
          }, 100)
        }}
        onSuccess={() => {
          // Don't do anything here - let the useEffect handle it
        }}
        initialView={authModalView}
      />
    </>
  )
}