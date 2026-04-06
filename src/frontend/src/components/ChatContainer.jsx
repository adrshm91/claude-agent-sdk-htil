import { useEffect, useRef } from 'react'
import { Bot, Plus, Loader2 } from 'lucide-react'
import Message from './Message.jsx'
import MessageInput from './MessageInput.jsx'

export default function ChatContainer({ messages, isStreaming, sessionId, meta, status, onSend, onNewSession }) {
  const bottomRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const shortId = sessionId ? sessionId.slice(0, 8) + '…' : null

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 shrink-0">
        <Bot size={20} className="text-violet-400" />
        <span className="font-semibold text-gray-100 text-sm">Claude Agent</span>

        {shortId && (
          <div className="flex items-center gap-2 ml-2 px-2.5 py-1 bg-gray-800 rounded-lg text-xs text-gray-400 font-mono">
            <span>{shortId}</span>
            {meta && (
              <span className="text-gray-500">
                · ${meta.cost_usd?.toFixed(4) ?? '—'} · {meta.num_turns} turn{meta.num_turns !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}

        <button
          onClick={onNewSession}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-100 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <Plus size={13} />
          New Session
        </button>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-4 messages-area">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot size={40} className="text-gray-700 mb-3" />
            <p className="text-gray-500 text-sm">Start a conversation with Claude</p>
          </div>
        )}
        {messages.map(msg => (
          <Message key={msg.id} msg={msg} sessionId={sessionId} />
        ))}
        <div ref={bottomRef} />
      </main>

      {/* Status bar */}
      {status === 'thinking' && (
        <div className="flex items-center gap-2 px-4 py-1.5 text-xs text-violet-400 border-t border-gray-800 bg-gray-950 shrink-0">
          <Loader2 size={12} className="animate-spin" />
          Thinking…
        </div>
      )}

      {/* Input */}
      <MessageInput onSend={onSend} isStreaming={isStreaming} />
    </div>
  )
}
