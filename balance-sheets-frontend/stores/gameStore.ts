import { create } from 'zustand'
import { GameState, GameCompany, GuessResult } from '@/types'

interface GameStore extends GameState {
  setCurrentCompany: (company: GameCompany | null) => void
  setIsRevealing: (isRevealing: boolean) => void
  submitGuess: (guess: number) => void
  nextCompany: () => void
  resetGame: () => void
}

const initialState: GameState = {
  currentCompany: null,
  score: 0,
  matches: 0,
  totalGuesses: 0,
  streak: 0,
  isRevealing: false,
  lastGuess: null,
  guessHistory: [],
}

export const useGameStore = create<GameStore>((set) => ({
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

      return {
        lastGuess: guess,
        isRevealing: true,
        totalGuesses: state.totalGuesses + 1,
        matches: isMatch ? state.matches + 1 : state.matches,
        score: isMatch ? state.score + 100 : state.score,
        streak: isMatch ? state.streak + 1 : 0,
        guessHistory: [...state.guessHistory, guessResult],
      }
    }),

  nextCompany: () =>
    set((state) => ({
      currentCompany: null,
      isRevealing: false,
      lastGuess: null,
    })),

  resetGame: () => set(initialState),
}))