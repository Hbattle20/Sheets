import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import Anthropic from '@anthropic-ai/sdk'

// Initialize Anthropic client
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
})

// Initialize Supabase client with service role for server-side operations
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// System prompt for Claude
const SYSTEM_PROMPT = `You are a financial analyst assistant helping users understand company financials. 
You have access to historical financial data including balance sheets, income statements, cash flow statements, 
and key financial metrics like P/E ratio, P/B ratio, ROE, and debt-to-equity ratios.

Provide insightful, accurate analysis based on the financial data provided. Be concise but thorough. 
If you notice concerning trends or important changes between years, mention them objectively.
Always cite specific numbers when making claims.
Focus on explaining financial trends, ratios, and what they mean for the company's health and valuation.
If you don't have enough information to answer a question, say so clearly.`

interface ChatRequest {
  message: string
  companyId: number
  sessionId: string
}

export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body: ChatRequest = await request.json()
    const { message, companyId, sessionId } = body

    // Validate inputs
    if (!message || !companyId || !sessionId) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // Get company info
    const { data: company, error: companyError } = await supabase
      .from('companies')
      .select('ticker, name')
      .eq('id', companyId)
      .single()

    if (companyError || !company) {
      console.error('Error fetching company:', companyError)
      return NextResponse.json(
        { error: 'Company not found' },
        { status: 404 }
      )
    }

    // Fetch financial data for the company
    const { data: financialData, error: financialError } = await supabase
      .from('financial_snapshots')
      .select(`
        *,
        company_metrics (*)
      `)
      .eq('company_id', companyId)
      .order('period_end_date', { ascending: false })
      .limit(10) // Get last 10 periods

    if (financialError || !financialData || financialData.length === 0) {
      console.error('Error fetching financial data:', financialError)
      return NextResponse.json(
        { error: 'Could not retrieve financial data' },
        { status: 500 }
      )
    }

    // Fetch market data
    const { data: marketData } = await supabase
      .from('market_data')
      .select('market_cap, stock_price, updated_at')
      .eq('company_id', companyId)
      .single()

    // Build context from financial data
    let context = `Company: ${company.name} (${company.ticker})\n\n`
    
    if (marketData) {
      context += `Current Market Data:\n`
      context += `- Market Cap: $${(marketData.market_cap / 1e9).toFixed(2)}B\n`
      context += `- Stock Price: $${marketData.stock_price.toFixed(2)}\n\n`
    }

    context += `Historical Financial Data (most recent periods first):\n\n`

    for (const snapshot of financialData) {
      const year = new Date(snapshot.period_end_date).getFullYear()
      const metrics = snapshot.company_metrics?.[0]
      
      context += `${year} Financial Snapshot:\n`
      context += `- Revenue: $${(snapshot.revenue / 1e9).toFixed(2)}B\n`
      context += `- Net Income: $${(snapshot.net_income / 1e9).toFixed(2)}B\n`
      context += `- Total Assets: $${(snapshot.total_assets / 1e9).toFixed(2)}B\n`
      context += `- Total Equity: $${(snapshot.total_equity / 1e9).toFixed(2)}B\n`
      context += `- Operating Cash Flow: $${(snapshot.operating_cash_flow / 1e9).toFixed(2)}B\n`
      
      if (metrics) {
        context += `- P/E Ratio: ${metrics.p_e_ratio?.toFixed(2) || 'N/A'}\n`
        context += `- P/B Ratio: ${metrics.p_b_ratio?.toFixed(2) || 'N/A'}\n`
        context += `- ROE: ${metrics.roe ? (metrics.roe * 100).toFixed(1) + '%' : 'N/A'}\n`
        context += `- Debt to Equity: ${metrics.debt_to_equity?.toFixed(2) || 'N/A'}\n`
      }
      
      context += '\n'
    }

    // Step 4: Call Claude API with context
    const response = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      temperature: 0.3, // Lower temperature for more factual responses
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user',
          content: `Context:\n${context}\n\nQuestion: ${message}`,
        },
      ],
    })

    // Extract the response text
    const assistantMessage = response.content[0].type === 'text' 
      ? response.content[0].text 
      : 'I apologize, but I was unable to generate a response.'

    // Log token usage for monitoring
    console.log(`Token usage - Input: ${response.usage?.input_tokens}, Output: ${response.usage?.output_tokens}`)

    // Return the response in the expected format
    return NextResponse.json({
      message: {
        id: Date.now().toString(),
        role: 'assistant',
        content: assistantMessage,
        timestamp: new Date().toISOString()
      },
      usage: {
        input_tokens: response.usage?.input_tokens || 0,
        output_tokens: response.usage?.output_tokens || 0,
      },
    })

  } catch (error) {
    console.error('Chat API error:', error)
    
    // Handle specific error types
    if (error instanceof Anthropic.APIError) {
      if (error.status === 401) {
        return NextResponse.json(
          { error: 'Invalid API key. Please check your Anthropic API key.' },
          { status: 401 }
        )
      } else if (error.status === 429) {
        return NextResponse.json(
          { error: 'Rate limit exceeded. Please try again later.' },
          { status: 429 }
        )
      }
    }

    return NextResponse.json(
      { error: 'An error occurred while processing your request' },
      { status: 500 }
    )
  }
}