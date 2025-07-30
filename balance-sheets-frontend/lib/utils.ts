import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const formatCurrency = (num: number): string => {
  const isNegative = num < 0
  const absNum = Math.abs(num)
  
  let formatted = ''
  if (absNum >= 1e12) {
    formatted = `$${(absNum / 1e12).toFixed(1)}T`
  } else if (absNum >= 1e9) {
    formatted = `$${(absNum / 1e9).toFixed(1)}B`
  } else if (absNum >= 1e6) {
    formatted = `$${(absNum / 1e6).toFixed(1)}M`
  } else {
    formatted = `$${absNum.toFixed(0)}`
  }
  
  return isNegative ? `-${formatted}` : formatted
}

export const formatRatio = (ratio: number, type: 'pe' | 'pb' | 'de'): string => {
  if (!ratio || ratio < 0) return 'N/A'
  if (type === 'de') return `${(ratio * 100).toFixed(0)}%`
  return ratio.toFixed(1)
}

export const parseMarketCapGuess = (input: string): number => {
  const cleaned = input.replace(/[$,\s]/g, '')
  const match = cleaned.match(/^(\d+(?:\.\d+)?)\s*([BTM])?$/i)
  if (!match) return 0
  
  const num = parseFloat(match[1])
  const suffix = match[2]?.toUpperCase()
  
  switch (suffix) {
    case 'T': return num * 1e12
    case 'B': return num * 1e9
    case 'M': return num * 1e6
    default: return num
  }
}

export const isMatch = (guess: number, actual: number): boolean => {
  return guess >= actual
}

export const calculatePercentageDiff = (guess: number, actual: number): number => {
  return ((guess - actual) / actual) * 100
}