'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function TestSupabase() {
  const [results, setResults] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function testConnection() {
      const tests: any = {}

      // Test 1: Basic connection
      try {
        const { data, error } = await supabase
          .from('companies')
          .select('*')
          .limit(1)
        
        tests.companiesTable = { data, error }
      } catch (e) {
        tests.companiesTable = { error: e }
      }

      // Test 2: Check quarterly data
      try {
        const { data: quarterlyData, error: quarterlyError } = await supabase
          .from('financial_snapshots')
          .select('company_id, period_end_date, report_type, revenue')
          .eq('report_type', '10-Q')
          .limit(10)
        
        tests.quarterlySnapshots = { data: quarterlyData, error: quarterlyError }
        
        // Count quarterly vs annual
        const { count: annualCount } = await supabase
          .from('financial_snapshots')
          .select('*', { count: 'exact', head: true })
          .eq('report_type', '10-K')
          
        const { count: quarterlyCount } = await supabase
          .from('financial_snapshots')
          .select('*', { count: 'exact', head: true })
          .eq('report_type', '10-Q')
          
        tests.reportTypeCounts = { annual: annualCount, quarterly: quarterlyCount }
      } catch (e) {
        tests.quarterlySnapshots = { error: e }
      }

      // Test 3: Check all tables
      const tables = ['companies', 'financial_snapshots', 'market_data', 'company_metrics']
      
      for (const table of tables) {
        try {
          const { count, error } = await supabase
            .from(table)
            .select('*', { count: 'exact', head: true })
          
          tests[`${table}_count`] = { count, error }
        } catch (e) {
          tests[`${table}_count`] = { error: e }
        }
      }

      setResults(tests)
      setLoading(false)
    }

    testConnection()
  }, [])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Supabase Connection Test</h1>
      
      <div className="mb-4">
        <p><strong>URL:</strong> {process.env.NEXT_PUBLIC_SUPABASE_URL}</p>
        <p><strong>Key (first 20 chars):</strong> {process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.substring(0, 20)}...</p>
      </div>

      {loading ? (
        <p>Testing connection...</p>
      ) : (
        <pre className="bg-gray-100 p-4 rounded overflow-auto">
          {JSON.stringify(results, null, 2)}
        </pre>
      )}
    </div>
  )
}