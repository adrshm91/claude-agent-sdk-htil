import { useCallback, useRef, useState } from 'react'
import { streamMessage } from '../api/client.js'

/**
 * Each message in the `messages` array has this shape:
 * {
 *   id: string,
 *   role: 'user' | 'assistant',
 *   type: 'text' | 'tool_use' | 'permission' | 'error',
 *   content: string,          // for text / error
 *   streaming: boolean,       // true while text is still arriving
 *   toolName: string,         // for tool_use
 *   toolInput: object,        // for tool_use
 *   permission: object,       // for permission
 * }
 */

let idCounter = 0
const uid = () => String(++idCounter)

export function useAgent() {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [meta, setMeta] = useState(null) // { cost_usd, num_turns }
  const [status, setStatus] = useState('ready') // 'ready' | 'thinking' | 'error'

  // Ref to track the current assistant text bubble id during a stream
  const assistantBubbleId = useRef(null)

  const updateMessage = useCallback((id, patch) => {
    setMessages(prev =>
      prev.map(m => (m.id === id ? { ...m, ...patch } : m))
    )
  }, [])

  const handleEvent = useCallback(
    (event) => {
      switch (event.type) {
        case 'text': {
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
                  ? { ...m, content: m.content + event.content }
                  : m
              )
            )
          }
          break
        }

        case 'tool_use': {
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
          setMessages(prev => [
            ...prev,
            {
              id: uid(),
              role: 'assistant',
              type: 'permission',
              permission: event.permission,
              streaming: false,
            },
          ])
          break
        }

        case 'result': {
          if (event.session_id) setSessionId(event.session_id)
          setMeta({ cost_usd: event.cost_usd, num_turns: event.num_turns })
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
    async (text) => {
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
        setMessages(prev => [
          ...prev,
          { id: uid(), role: 'assistant', type: 'error', content: err.message, streaming: false },
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
