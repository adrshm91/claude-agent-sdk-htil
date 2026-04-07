import { useCallback, useRef, useState, ChangeEvent, KeyboardEvent } from 'react'
import { ArrowUp, Square } from 'lucide-react'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Card } from './ui/card'

interface MessageInputProps {
  onSend: (text: string) => void
  isStreaming: boolean
}

export default function MessageInput({ onSend, isStreaming }: MessageInputProps) {
  const [text, setText] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [])

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    autoResize()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  return (
    <div className="border-t border-border px-4 py-3 bg-card">
      <Card className="bg-background border-input focus-within:border-primary transition-colors">
        <div className="flex items-end gap-2 p-3">
          <Textarea
            ref={textareaRef}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder="Message Claude…"
            disabled={isStreaming}
            className="flex-1 bg-transparent border-0 resize-none outline-none min-h-[24px] max-h-[200px] leading-6 p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            rows={1}
          />
          <Button
            onClick={submit}
            disabled={isStreaming || !text.trim()}
            size="icon"
            className="shrink-0 h-8 w-8 bg-primary hover:bg-primary/80"
          >
            {isStreaming ? (
              <Square size={14} className="fill-current" />
            ) : (
              <ArrowUp size={16} />
            )}
          </Button>
        </div>
      </Card>
      <p className="text-center text-xs text-muted-foreground mt-2">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  )
}
