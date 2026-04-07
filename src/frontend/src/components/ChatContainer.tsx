import { useEffect, useRef } from 'react'
import { Bot, Plus, Loader2 } from 'lucide-react'
import Message from './Message.tsx'
import MessageInput from './MessageInput.tsx'
import { ScrollArea } from './ui/scroll-area'
import { Badge } from './ui/badge'
import { Message as MessageType, Meta } from '../hooks/useAgent'

interface ChatContainerProps {
  messages: MessageType[]
  isStreaming: boolean
  sessionId: string | null
  meta: Meta | null
  status: 'ready' | 'thinking' | 'error'
  onSend: (text: string) => void
  onNewSession: () => void
}

export default function ChatContainer({ messages, isStreaming, sessionId, meta, status, onSend, onNewSession }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const shortId = sessionId ? sessionId.slice(0, 8) + '…' : null

  return (
    <div className="flex flex-col h-screen bg-background px-4">
      <div className="flex flex-col h-screen max-w-4xl mx-auto w-full">
        {/* Header */}
        <header className="flex items-center gap-2 px-2 py-3 border-b border-border bg-card shrink-0 overflow-visible">
        <Bot size={20} className="text-primary shrink-0" />
        <h1 className="font-semibold text-foreground text-sm shrink-0">Claude Agent</h1>

        {shortId && (
          <div className="hidden sm:flex items-center gap-1 ml-2 px-2 py-1 bg-muted/50 border border-muted-foreground/20 rounded-md shrink-0">
            <Badge variant="outline" className="font-mono text-xs px-1.5 py-0.5">
              {shortId}
            </Badge>
            {meta && (
              <span className="text-muted-foreground text-xs whitespace-nowrap">
                ${meta.cost_usd?.toFixed(3) ?? '—'}
              </span>
            )}
          </div>
        )}

        <button
          onClick={onNewSession}
          className="ml-auto shrink-0 text-xs h-9 px-3 rounded-md border border-muted-foreground/20 text-muted-foreground bg-transparent hover:bg-muted/50 hover:text-foreground hover:border-muted-foreground/40 transition-colors inline-flex items-center justify-center gap-2"
        >
          <Plus size={12} className="mr-1" />
          <span className="hidden sm:inline">New Session</span>
          <span className="sm:hidden">New</span>
        </button>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <main className="px-4 py-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
              <Bot size={40} className="text-muted-foreground mb-3" />
              <p className="text-muted-foreground text-sm">Start a conversation with Claude</p>
            </div>
          )}
          {messages.map(msg => (
            <Message key={msg.id} msg={msg} sessionId={sessionId} />
          ))}
          <div ref={bottomRef} />
        </main>
      </ScrollArea>

      {/* Status bar */}
      {status === 'thinking' && (
        <div className="flex items-center gap-2 px-4 py-1.5 border-t border-border bg-card shrink-0">
          <Loader2 size={12} className="animate-spin text-primary" />
          <span className="text-sm text-primary">Thinking…</span>
        </div>
      )}

        {/* Input */}
        <MessageInput onSend={onSend} isStreaming={isStreaming} />
      </div>
    </div>
  )
}
