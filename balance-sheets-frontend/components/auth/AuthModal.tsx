'use client'

import { useState, useEffect } from 'react'
import { SignInForm } from './SignInForm'
import { SignUpForm } from './SignUpForm'
import { PasswordReset } from './PasswordReset'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  initialView?: 'signin' | 'signup'
  onSuccess?: () => void
}

type AuthView = 'signin' | 'signup' | 'reset'

export function AuthModal({ isOpen, onClose, initialView = 'signin', onSuccess }: AuthModalProps) {
  const [view, setView] = useState<AuthView>(initialView)

  useEffect(() => {
    setView(initialView)
  }, [initialView])

  if (!isOpen) return null

  const handleSuccess = () => {
    // For sign up, we close the modal but don't reset view immediately
    // This allows the toast to show while modal fades out
    if (view === 'signup') {
      onClose()
      // Reset view after a longer delay for sign up
      setTimeout(() => setView(initialView), 1000)
    } else {
      onClose()
      // Reset to initial view for next time
      setTimeout(() => setView(initialView), 300)
    }
    
    // Call the parent's onSuccess callback if provided
    onSuccess?.()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6 animate-fade-in">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* Content */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {view === 'signin' && 'Welcome back'}
              {view === 'signup' && 'Create an account'}
              {view === 'reset' && 'Reset password'}
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              {view === 'signin' && 'Sign in to save your matches and track your progress'}
              {view === 'signup' && 'Join to save your matches and compete with others'}
              {view === 'reset' && 'We\'ll help you get back into your account'}
            </p>
          </div>

          {view === 'signin' && (
            <SignInForm
              onSuccess={handleSuccess}
              onSignUpClick={() => setView('signup')}
              onForgotPasswordClick={() => setView('reset')}
            />
          )}

          {view === 'signup' && (
            <SignUpForm
              onSuccess={handleSuccess}
              onSignInClick={() => setView('signin')}
            />
          )}

          {view === 'reset' && (
            <PasswordReset
              onBackToSignIn={() => setView('signin')}
            />
          )}
        </div>
      </div>
    </div>
  )
}