'use client'

import { Button } from '@/components/ui/Button'

interface MatchAuthPromptProps {
  isOpen: boolean
  onSignUp: () => void
  onSignIn: () => void
  onMaybeLater: () => void
}

export function MatchAuthPrompt({ isOpen, onSignUp, onSignIn, onMaybeLater }: MatchAuthPromptProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-8 animate-fade-in text-center">
          {/* Success Icon */}
          <div className="mb-6">
            <div className="mx-auto w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          {/* Content */}
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Congratulations! It's a match! 🎉
          </h2>
          <p className="text-gray-600 mb-8">
            Sign up to reveal the company and save your winning streak. Track your progress and compete with others!
          </p>

          {/* Actions */}
          <div className="space-y-3">
            <Button 
              onClick={onSignUp} 
              className="w-full"
              size="lg"
            >
              Sign up to reveal match
            </Button>
            
            <Button 
              onClick={onSignIn} 
              variant="outline" 
              className="w-full"
            >
              Already have an account? Sign in
            </Button>
            
            <button
              onClick={onMaybeLater}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}