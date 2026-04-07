import { useCallback, useRef, useState } from 'react'
import { streamMessage } from '../api/client.ts'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  type: 'text' | 'tool_use' | 'permission' | 'error'
  content?: string          // for text / error
  streaming: boolean       // true while text is still arriving
  toolName?: string        // for tool_use
  toolInput?: any          // for tool_use
  permission?: any         // for permission
}

export interface Meta {
  cost_usd: number
  num_turns: number
}

export interface StreamEvent {
  type: 'text' | 'tool_use' | 'permission' | 'result' | 'done' | 'error'
  content?: string
  tool_name?: string
  tool_input?: any
  permission?: any
  session_id?: string
  cost_usd?: number
  num_turns?: number
  error?: string
}

let idCounter = 0
const uid = () => String(++idCounter)

export function useAgent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [status, setStatus] = useState<'ready' | 'thinking' | 'error'>('ready')

  // Ref to track the current assistant text bubble id during a stream
  const assistantBubbleId = useRef<string | null>(null)

  const updateMessage = useCallback((id: string, patch: Partial<Message>) => {
    setMessages(prev =>
      prev.map(m => (m.id === id ? { ...m, ...patch } : m))
    )
  }, [])

  const handleEvent = useCallback(
    (event: StreamEvent) => {
      switch (event.type) {
        case 'text': {
          // Update session ID if provided in text event
          if (event.session_id && !sessionId) setSessionId(event.session_id)

          if (!assistantBubbleId.current) {
            // First text chunk — create the assistant bubble
            const id = uid()
            assistantBubbleId.current = id
            setMessages(prev => [
              ...prev,
              { id, role: 'assistant', type: 'text', content: event.content, streaming: true },
            ])
          } else {
            // Append to existing bubble
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantBubbleId.current
                  ? { ...m, content: (m.content || '') + (event.content || '') }
                  : m
              )
            )
          }
          break
        }

        case 'tool_use': {
          // Update session ID if provided
          if (event.session_id && !sessionId) setSessionId(event.session_id)

          // Finalize any open text bubble first
          if (assistantBubbleId.current) {
            updateMessage(assistantBubbleId.current, { streaming: false })
            assistantBubbleId.current = null
          }
          setMessages(prev => [
            ...prev,
            {
              id: uid(),
              role: 'assistant',
              type: 'tool_use',
              toolName: event.tool_name,
              toolInput: event.tool_input,
              streaming: false,
            },
          ])
          break
        }

        case 'permission': {
          // Update session ID if provided in permission event
          if (event.session_id) setSessionId(event.session_id)
          setMessages(prev => [
            ...prev,
            {
              id: uid(),
              role: 'assistant',
              type: 'permission',
              permission: { ...event.permission, session_id: event.session_id },
              streaming: false,
            },
          ])
          break
        }

        case 'result': {
          if (event.session_id) setSessionId(event.session_id)
          setMeta({
            cost_usd: event.cost_usd || 0,
            num_turns: event.num_turns || 0
          })
          break
        }

        case 'done': {
          if (event.session_id) setSessionId(event.session_id)
          // Finalize streaming bubble
          if (assistantBubbleId.current) {
            updateMessage(assistantBubbleId.current, { streaming: false })
            assistantBubbleId.current = null
          }
          setIsStreaming(false)
          setStatus('ready')
          break
        }

        case 'error': {
          if (assistantBubbleId.current) {
            updateMessage(assistantBubbleId.current, { streaming: false })
            assistantBubbleId.current = null
          }
          setMessages(prev => [
            ...prev,
            { id: uid(), role: 'assistant', type: 'error', content: event.error, streaming: false },
          ])
          setIsStreaming(false)
          setStatus('error')
          break
        }

        default:
          break
      }
    },
    [updateMessage]
  )

  const sendMessage = useCallback(
    async (text: string) => {
      if (isStreaming || !text.trim()) return

      assistantBubbleId.current = null

      // Optimistic user bubble
      setMessages(prev => [
        ...prev,
        { id: uid(), role: 'user', type: 'text', content: text, streaming: false },
      ])

      setIsStreaming(true)
      setStatus('thinking')

      try {
        await streamMessage(text, sessionId, handleEvent)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
        setMessages(prev => [
          ...prev,
          { id: uid(), role: 'assistant', type: 'error', content: errorMessage, streaming: false },
        ])
        setIsStreaming(false)
        setStatus('error')
      }
    },
    [isStreaming, sessionId, handleEvent]
  )

  const newSession = useCallback(() => {
    setMessages([])
    setSessionId(null)
    setMeta(null)
    setStatus('ready')
    setIsStreaming(false)
    assistantBubbleId.current = null
  }, [])

  return { messages, isStreaming, sessionId, meta, status, sendMessage, newSession }
}
