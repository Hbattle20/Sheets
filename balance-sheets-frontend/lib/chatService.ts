import { ChatMessage } from '@/types'

interface ChatRequest {
  message: string
  companyContext: {
    id: number
    name: string
    financialData?: any
  }
  sessionId?: string
}

interface ChatResponse {
  message: ChatMessage
}

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: request.message,
          companyId: request.companyContext.id,
          companyName: request.companyContext.name,
          financialData: request.companyContext.financialData,
          sessionId: request.sessionId || 'default'
        })
      })
      
      if (!response.ok) {
        // Handle specific error cases
        if (response.status === 429) {
          throw new Error('Too many requests. Please try again later.')
        }
        if (response.status === 401) {
          throw new Error('Please sign in to use the chat feature.')
        }
        if (response.status === 500) {
          throw new Error('Server error. Please try again later.')
        }
        
        // Generic error for other status codes
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `Request failed with status ${response.status}`)
      }
      
      const data = await response.json()
      
      // Ensure the response has the expected structure
      if (!data.message || !data.message.id || !data.message.content) {
        throw new Error('Invalid response format from server')
      }
      
      // Convert timestamp string to Date object if needed
      if (typeof data.message.timestamp === 'string') {
        data.message.timestamp = new Date(data.message.timestamp)
      }
      
      return {
        message: {
          id: data.message.id,
          role: data.message.role || 'assistant',
          content: data.message.content,
          timestamp: data.message.timestamp
        }
      }
    } catch (error) {
      // Log error for debugging
      console.error('Chat service error:', error)
      
      // Re-throw with a user-friendly message if it's not already an Error
      if (error instanceof Error) {
        throw error
      } else {
        throw new Error('Failed to send message. Please try again.')
      }
    }
  }
}