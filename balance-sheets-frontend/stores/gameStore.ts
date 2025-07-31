import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { GameState, GameCompany, GuessResult } from '@/types'
import { supabase } from '@/lib/supabase'

interface SavedMatch {
  company: GameCompany
  guess: number
  actual: number
  isMatch: boolean
  percentageDiff: number
  timestamp: Date
}

interface GameStore extends GameState {
  savedMatches: SavedMatch[]
  setCurrentCompany: (company: GameCompany | null) => void
  setIsRevealing: (isRevealing: boolean) => void
  submitGuess: (guess: number) => void
  nextCompany: () => void
  resetGame: () => void
}

const initialState: GameState & { savedMatches: SavedMatch[] } = {
  currentCompany: null,
  score: 0,
  matches: 0,
  totalGuesses: 0,
  streak: 0,
  isRevealing: false,
  lastGuess: null,
  guessHistory: [],
  savedMatches: [],
}

export const useGameStore = create<GameStore>()(
  persist(
    (set) => ({
      ...initialState,

      setCurrentCompany: (company) => set({ currentCompany: company }),
      
      setIsRevealing: (isRevealing) => set({ isRevealing }),

      submitGuess: (guess) =>
        set((state) => {
          if (!state.currentCompany) return state

          const actual = state.currentCompany.hiddenData.market_cap
          const isMatch = guess >= actual
          const percentageDiff = ((guess - actual) / actual) * 100

          const guessResult: GuessResult = {
            companyId: state.currentCompany.id,
            companyName: state.currentCompany.hiddenData.name,
            guess,
            actual,
            isMatch,
            percentageDiff,
            timestamp: new Date(),
          }

          // Save match if successful
          const savedMatches = isMatch ? [
            ...state.savedMatches,
            {
              company: state.currentCompany,
              guess,
              actual,
              isMatch,
              percentageDiff,
              timestamp: new Date(),
            }
          ] : state.savedMatches

          // Save to database if user is authenticated
          const saveToDatabase = async () => {
            const { data: { user } } = await supabase.auth.getUser()
            
            if (user) {
              try {
                await supabase
                  .from('user_matches')
                  .insert({
                    user_id: user.id,
                    company_id: state.currentCompany!.id,
                    guess: guess,
                    actual_market_cap: actual,
                    is_match: isMatch,
                    percentage_diff: percentageDiff,
                  })
              } catch (error) {
                console.error('Error saving match to database:', error)
              }
            }
          }

          // Execute database save asynchronously
          saveToDatabase()

          return {
            lastGuess: guess,
            isRevealing: true,
            totalGuesses: state.totalGuesses + 1,
            matches: isMatch ? state.matches + 1 : state.matches,
            score: isMatch ? state.score + 100 : state.score,
            streak: isMatch ? state.streak + 1 : 0,
            guessHistory: [...state.guessHistory, guessResult],
            savedMatches,
          }
        }),

      nextCompany: () =>
        set((state) => ({
          currentCompany: null,
          isRevealing: false,
          lastGuess: null,
        })),

      resetGame: () => set(initialState),
    }),
    {
      name: 'buffett-sheets-storage',
      partialize: (state) => ({ savedMatches: state.savedMatches }),
    }
  )
)