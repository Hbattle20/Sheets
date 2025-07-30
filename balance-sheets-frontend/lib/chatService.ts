import { ChatMessage } from '@/types'

interface ChatRequest {
  message: string
  companyContext: {
    id: number
    name: string
    financialData?: any
  }
}

interface ChatResponse {
  message: ChatMessage
}

// This service can be easily swapped to call your backend API later
export const chatService = {
  // Mock implementation for now
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Mock response
    const mockResponse: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `[Mock Response] Analyzing ${request.companyContext.name}... ${request.message}`,
      timestamp: new Date()
    }
    
    return { message: mockResponse }
  },

  // Future implementation will look like:
  // async sendMessage(request: ChatRequest): Promise<ChatResponse> {
  //   const response = await fetch('http://localhost:8000/api/chat', {
  //     method: 'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify(request)
  //   })
  //   return response.json()
  // }
}