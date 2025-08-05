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
const SYSTEM_PROMPT = `You are a financial analyst assistant with access to comprehensive 10-K filings from multiple years. 
You have access to all sections including:
- Item 1: Business overview and strategy  
- Item 1A: Risk Factors
- Item 7: Management's Discussion and Analysis (MD&A) with financial results and forward-looking statements
- Item 8: Financial Statements and Supplementary Data
- And all other standard 10-K sections

You also have access to structured financial data including balance sheets, income statements, and key metrics.

When searching for information:
- Forward-looking statements often use phrases like "we expect", "we anticipate", "outlook", "guidance", "we believe", "we plan"
- Segment revenue (like Azure) is typically discussed in MD&A and business sections
- Year-over-year comparisons should cite specific numbers from different years

Provide insightful, accurate analysis based on the context provided. Be specific and cite exact figures when available.
If you notice trends across multiple years, highlight them. If the provided context doesn't contain the information needed, 
explain what specific data would be required to answer the question properly.`

interface ChatRequest {
  message: string
  companyId: number
  sessionId: string
  conversationDepth?: number // Track conversation depth for complexity assessment
}

// Model selection function
const determineModelComplexity = (
  message: string,
  relevantChunks: any[],
  conversationDepth: number = 0
): { model: string; reason: string } => {
  const lowerMessage = message.toLowerCase()
  
  // Complex analytical keywords that require Opus 4
  const complexKeywords = [
    'compare', 'analyze', 'thesis', 'hidden value', 'discrepancy',
    'forward-looking', 'guidance', 'actual results', 'versus actual',
    'margin analysis', 'forensic', 'pattern', 'trend across',
    'investment case', 'bull case', 'bear case', 'debate'
  ]
  
  // Simple query keywords that can use Sonnet 4
  const simpleKeywords = [
    'what is', 'what was', 'current', 'latest', 'definition',
    'mean', 'explain', 'ratio', 'revenue in', 'profit in'
  ]
  
  // Check for multi-year analysis
  const yearMatches = message.match(/\b(19|20)\d{2}\b/g) || []
  const uniqueYears = new Set(yearMatches)
  const isMultiYear = uniqueYears.size >= 3
  
  // Check for cross-company comparison
  const companyPattern = /\b(MSFT|AAPL|GOOGL|AMZN|META|NVDA|TSLA)\b/gi
  const companyMatches = message.match(companyPattern) || []
  const isMultiCompany = new Set(companyMatches.map(c => c.toUpperCase())).size > 1
  
  // High chunk count indicates complex query
  const hasHighChunkCount = relevantChunks.length >= 15
  
  // Deep conversation indicates complex analysis
  const isDeepConversation = conversationDepth >= 3
  
  // Check for complex analytical patterns
  const hasComplexKeywords = complexKeywords.some(keyword => lowerMessage.includes(keyword))
  const hasSimpleKeywords = simpleKeywords.some(keyword => lowerMessage.includes(keyword))
  
  // Decision logic
  if (isMultiCompany) {
    return {
      model: 'claude-opus-4-20250514',
      reason: 'Multi-company comparison detected'
    }
  }
  
  if (isMultiYear && hasComplexKeywords) {
    return {
      model: 'claude-opus-4-20250514',
      reason: 'Multi-year comparative analysis'
    }
  }
  
  if (hasHighChunkCount && !hasSimpleKeywords) {
    return {
      model: 'claude-opus-4-20250514',
      reason: 'High complexity query with many relevant chunks'
    }
  }
  
  if (isDeepConversation) {
    return {
      model: 'claude-opus-4-20250514',
      reason: 'Deep conversation requiring context continuity'
    }
  }
  
  if (hasComplexKeywords && !hasSimpleKeywords) {
    return {
      model: 'claude-opus-4-20250514',
      reason: 'Complex analytical keywords detected'
    }
  }
  
  // Default to Sonnet 4 for simple queries
  return {
    model: 'claude-sonnet-4-20250514',
    reason: hasSimpleKeywords ? 'Simple lookup query' : 'Standard query'
  }
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

    // Step 3: Add vector search for 10-K document chunks
    let relevantChunks: any[] = []

    try {
      // Generate embedding for the user's question
      const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: message,
          model: 'text-embedding-3-large',
        }),
      })

      if (embeddingResponse.ok) {
        const embeddingData = await embeddingResponse.json()
        const queryEmbedding = embeddingData.data[0].embedding

        // Search for relevant chunks using vector similarity
        const { data: vectorChunks, error: searchError } = await supabase.rpc(
          'search_similar_chunks',
          {
            query_embedding: queryEmbedding,
            match_count: 20, // Get top 20 most relevant chunks
            filter_ticker: company.ticker,
          }
        )

        if (!searchError && vectorChunks && vectorChunks.length > 0) {
          relevantChunks = vectorChunks
          
          // Add 10-K context to the existing context
          context += `\n\nRelevant excerpts from 10-K filings:\n\n`
          
          // Sort chunks by year and section
          relevantChunks.sort((a, b) => {
            const yearA = new Date(a.filing_date).getFullYear()
            const yearB = new Date(b.filing_date).getFullYear()
            if (yearA !== yearB) return yearB - yearA
            return a.section.localeCompare(b.section)
          })

          for (const chunk of relevantChunks) {
            const year = new Date(chunk.filing_date).getFullYear()
            context += `[${year} - ${chunk.section}]\n${chunk.text}\n\n---\n\n`
          }
        }
      }
    } catch (error) {
      // Vector search not available, using fallback
    }

    // Fallback: Use keyword search if vector search didn't work
    if (relevantChunks.length < 5) {
      
      // Extract keywords from message
      const keywords = message.toLowerCase()
      const searchConditions = []
      
      if (keywords.includes('azure') || keywords.includes('cloud')) {
        searchConditions.push('text.ilike.%azure%', 'text.ilike.%cloud%')
      }
      if (keywords.includes('forward') || keywords.includes('outlook') || keywords.includes('guidance')) {
        searchConditions.push('text.ilike.%expect%', 'text.ilike.%anticipate%', 'text.ilike.%outlook%')
      }
      if (keywords.includes('margin')) {
        searchConditions.push('text.ilike.%margin%', 'text.ilike.%operating margin%')
      }
      if (keywords.includes('risk')) {
        searchConditions.push('text.ilike.%risk%')
      }
      
      if (searchConditions.length > 0) {
        const { data: keywordChunks } = await supabase
          .from('document_chunks')
          .select('chunk_id, ticker, filing_date, section, text, metadata')
          .eq('ticker', company.ticker)
          .or(searchConditions.join(','))
          .limit(10)

        if (keywordChunks && keywordChunks.length > 0) {
          context += `\n\nRelevant excerpts from 10-K filings (keyword search):\n\n`
          for (const chunk of keywordChunks) {
            const year = new Date(chunk.filing_date).getFullYear()
            context += `[${year} - ${chunk.section}]\n${chunk.text}\n\n---\n\n`
          }
        }
      }
    }

    // Limit context length
    if (context.length > 100000) {
      context = context.substring(0, 100000) + '\n\n[Context truncated due to length]'
    }

    // Determine which model to use based on query complexity
    const conversationDepth = body.conversationDepth || 0
    const modelSelection = determineModelComplexity(message, relevantChunks, conversationDepth)
    
    
    // Step 4: Call Claude API with context
    const response = await anthropic.messages.create({
      model: modelSelection.model,
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
        model: modelSelection.model,
        model_reason: modelSelection.reason
      },
      debug: {
        chunks_found: relevantChunks.length,
        model_used: modelSelection.model,
        selection_reason: modelSelection.reason
      }
    })

  } catch (error) {
    
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