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

  // Watch for authentication changes when waiting
  useEffect(() => {
    // Check if user just signed in (was null, now has value)
    if (!previousUser && user && waitingForAuth) {
      // User just authenticated, save the match to database
      const saveMatch = async () => {
        if (lastGuess && company) {
          const isMatch = lastGuess >= company.hiddenData.market_cap
          
          // Only save if it was actually a match
          if (!isMatch) {
            return
          }
          
          try {
            const { error } = await supabase
              .from('user_matches')
              .insert({
                user_id: user.id,
                company_id: company.id,
                guess: lastGuess,
                actual_market_cap: company.hiddenData.market_cap,
                is_match: isMatch,
                percentage_diff: ((lastGuess - company.hiddenData.market_cap) / company.hiddenData.market_cap) * 100,
              })
              
            if (error) {
              console.error('Error saving match after authentication:', error)
            }
          } catch (error) {
            console.error('Error saving match after authentication:', error)
          }
        }
      }
      
      saveMatch()
      
      // Proceed with reveal
      setWaitingForAuth(false)
      setShowAuthModal(false)
    }
    
    // Update previous user for next render
    if (user !== previousUser) {
      setPreviousUser(user)
    }
  }, [user, waitingForAuth, lastGuess, company, previousUser])

  const handleGuessSubmit = () => {
    setHasGuessed(true)
    
    // We'll check for match after the guess is processed
    setTimeout(() => {
      const store = useGameStore.getState()
      const currentGuess = store.lastGuess
      
      // Check if it's a match and user is not authenticated
      if (currentGuess && currentGuess >= company.hiddenData.market_cap && !user) {
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