'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { parseValueEstimate } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'

interface GuessInputProps {
  onSubmit: () => void
}

interface FormData {
  guess: string
}

export default function GuessInput({ onSubmit }: GuessInputProps) {
  const { submitGuess } = useGameStore()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [displayValue, setDisplayValue] = useState('')
  
  const { register, handleSubmit, formState: { errors }, reset, setValue } = useForm<FormData>()

  const formatWithCommas = (value: string) => {
    // Remove all non-digit characters except decimal point and letters (B, T, M)
    const cleaned = value.replace(/[^0-9.BTMbtm]/g, '')
    
    // Split by decimal point
    const parts = cleaned.split('.')
    
    // Add commas to the integer part
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    
    // Rejoin with decimal if it exists
    return parts.join('.')
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value
    const formatted = formatWithCommas(rawValue)
    setDisplayValue(formatted)
    setValue('guess', formatted)
  }

  const onFormSubmit = async (data: FormData) => {
    const marketCapValue = parseValueEstimate(data.guess)
    
    if (marketCapValue === 0) {
      return
    }

    setIsSubmitting(true)
    submitGuess(marketCapValue)
    onSubmit()
    reset()
    setDisplayValue('')
    setIsSubmitting(false)
  }

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
      <div>
        <label htmlFor="guess" className="block text-sm font-medium text-gray-700 mb-2">
          Enter your company value estimate
        </label>
        <div className="flex space-x-2">
          <Input
            id="guess"
            type="text"
            placeholder="e.g., 500B or 1.2T"
            value={displayValue}
            {...register('guess', {
              required: 'Please enter a value estimate',
              pattern: {
                value: /^\$?\s*[\d,]+(?:\.\d+)?\s*[BTM]?$/i,
                message: 'Invalid format. Use numbers with optional B, T, or M suffix'
              }
            })}
            onChange={handleInputChange}
            disabled={isSubmitting}
            className="flex-1"
          />
          <Button type="submit" disabled={isSubmitting}>
            Submit Value
          </Button>
        </div>
        {errors.guess && (
          <p className="mt-1 text-sm text-red-600">{errors.guess.message}</p>
        )}
      </div>
      
      <p className="text-xs text-gray-500">
        Tip: You can use B for billions (e.g., 500B) or T for trillions (e.g., 1.2T)
      </p>
    </form>
  )
}