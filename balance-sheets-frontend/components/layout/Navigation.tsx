'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { AuthModal } from '@/components/auth/AuthModal'
import { Button } from '@/components/ui/Button'

export function Navigation() {
  const pathname = usePathname()
  const { user, signOut } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authModalView, setAuthModalView] = useState<'signin' | 'signup'>('signin')

  const tabs = [
    { name: 'Analyze', href: '/' },
    { name: 'Matches', href: '/matches' }
  ]

  const handleSignIn = () => {
    setAuthModalView('signin')
    setShowAuthModal(true)
  }

  const handleSignUp = () => {
    setAuthModalView('signup')
    setShowAuthModal(true)
  }

  const handleSignOut = async () => {
    await signOut()
  }

  return (
    <>
      <nav className="bg-white shadow-sm mb-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex space-x-8">
              {tabs.map((tab) => {
                const isMatchesTab = tab.href === '/matches'
                const isLocked = isMatchesTab && !user
                
                if (isLocked) {
                  return (
                    <button
                      key={tab.name}
                      onClick={handleSignIn}
                      className="py-4 px-1 border-b-2 font-medium text-sm transition-colors border-transparent text-gray-400 hover:text-gray-600 hover:border-gray-300 flex items-center gap-1"
                    >
                      {tab.name}
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                        />
                      </svg>
                    </button>
                  )
                }
                
                return (
                  <Link
                    key={tab.name}
                    href={tab.href}
                    className={cn(
                      'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
                      pathname === tab.href
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    )}
                  >
                    {tab.name}
                  </Link>
                )
              })}
            </div>
            
            <div className="flex items-center space-x-4">
              {user ? (
                <>
                  <span className="text-sm text-gray-600">
                    {user.email}
                  </span>
                  <Button
                    onClick={handleSignOut}
                    variant="outline"
                    size="sm"
                  >
                    Sign out
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    onClick={handleSignIn}
                    variant="outline"
                    size="sm"
                  >
                    Sign in
                  </Button>
                  <Button
                    onClick={handleSignUp}
                    size="sm"
                  >
                    Sign up
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initialView={authModalView}
      />
    </>
  )
}