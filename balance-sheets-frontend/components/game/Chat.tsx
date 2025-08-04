'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { chatService } from '@/lib/chatService'

interface ChatProps {
  companyName: string
  companyId: number
}

export function Chat({ companyName, companyId }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuth()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Create or load chat session
  useEffect(() => {
    const loadOrCreateSession = async () => {
      if (!user) return

      // Check for existing session
      const { data: existingSession } = await supabase
        .from('chat_sessions')
        .select('id')
        .eq('user_id', user.id)
        .eq('company_id', companyId)
        .single()

      if (existingSession) {
        setSessionId(existingSession.id)
        
        // Load messages from database
        const { data: dbMessages } = await supabase
          .from('chat_messages')
          .select('*')
          .eq('session_id', existingSession.id)
          .order('created_at', { ascending: true })

        if (dbMessages) {
          setMessages(dbMessages.map(msg => ({
            id: msg.id.toString(),
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            timestamp: new Date(msg.created_at)
          })))
        }
      } else {
        // Create new session
        const { data: newSession } = await supabase
          .from('chat_sessions')
          .insert({
            user_id: user.id,
            company_id: companyId
          })
          .select()
          .single()

        if (newSession) {
          setSessionId(newSession.id)
        }
      }
    }

    loadOrCreateSession()
  }, [companyId, user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !sessionId) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Save user message to database
    try {
      await supabase
        .from('chat_messages')
        .insert({
          session_id: sessionId,
          role: 'user',
          content: userMessage.content
        })
    } catch (error) {
      console.error('Error saving message:', error)
      setIsLoading(false)
      return
    }

    // Call the chat API
    try {
      const response = await chatService.sendMessage({
        message: userMessage.content,
        companyContext: {
          id: companyId,
          name: companyName
        },
        sessionId: sessionId.toString(),
        conversationDepth: messages.length
      })

      setMessages(prev => [...prev, response.message])
      
      // Log debug information if present
      if (response.debug) {
        console.log('Chat debug info:', response.debug)
      }
      
      // Save assistant message to database
      try {
        await supabase
          .from('chat_messages')
          .insert({
            session_id: sessionId,
            role: 'assistant',
            content: response.message.content
          })
      } catch (dbError) {
        console.error('Error saving assistant message:', dbError)
      }
    } catch (error) {
      console.error('Error calling chat API:', error)
      // Add error message to chat
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-lg border">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-sm">Ask Claude about {companyName}'s financials</p>
            <p className="text-xs mt-2">Example: "Why did revenue grow so much in 2021?"</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <p className="text-xs mt-1 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex space-x-2">
          <Input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the financials..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            Send
          </Button>
        </div>
      </form>
    </div>
  )
}