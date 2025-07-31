import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Navigation } from '@/components/layout/Navigation'
import { FeedbackButton } from '@/components/ui/FeedbackButton'
import { AuthProvider } from '@/contexts/AuthContext'
import { ToastProvider } from '@/contexts/ToastContext'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Buffett Sheets - Market Cap Guessing Game',
  description: 'Test your financial literacy by guessing company market caps',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <ToastProvider>
            <div className="min-h-screen bg-gray-50">
              <header className="text-center pt-8 pb-4">
                <h1 className="text-4xl font-bold text-gray-900 mb-2">
                  Buffett Sheets
                </h1>
                <p className="text-lg text-gray-600">
                  Guess the market cap based on financial data
                </p>
              </header>
              <Navigation />
              {children}
              <FeedbackButton />
            </div>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  )
}