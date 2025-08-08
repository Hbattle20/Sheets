'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

interface SignInFormProps {
  onSuccess?: () => void
  onSignUpClick?: () => void
  onForgotPasswordClick?: () => void
}

export function SignInForm({ onSuccess, onSignUpClick, onForgotPasswordClick }: SignInFormProps) {
  const { signIn, signInWithGoogle, signInWithApple } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email || !password) {
      setError('Please enter your email and password')
      return
    }

    setError(null)
    setLoading(true)

    const { error } = await signIn(email, password)

    if (error) {
      if (error.message.includes('Invalid login credentials')) {
        setError('Invalid email or password')
      } else if (error.message.includes('Email not confirmed')) {
        setError('Please check your email to confirm your account')
      } else {
        setError(error.message)
      }
      setLoading(false)
    } else {
      setLoading(false)
      onSuccess?.()
    }
  }

  const handleGoogle = async () => {
    setError(null)
    await signInWithGoogle()
  }

  const handleApple = async () => {
    setError(null)
    await signInWithApple()
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-2">
        <Button onClick={handleGoogle} variant="outline" className="w-full">
          Continue with Google
        </Button>
        <Button onClick={handleApple} variant="outline" className="w-full">
          Continue with Apple
        </Button>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-500">Or continue with email</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <Input
            id="email"
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <button
              type="button"
              onClick={onForgotPasswordClick}
              className="text-sm text-blue-600 hover:text-blue-500"
            >
              Forgot password?
            </button>
          </div>
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Signing in...' : 'Sign in'}
        </Button>

        <p className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSignUpClick}
            className="text-blue-600 hover:text-blue-500 font-medium"
          >
            Sign up
          </button>
        </p>
      </form>
    </div>
  )
}