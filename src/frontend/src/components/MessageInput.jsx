import { useCallback, useRef, useState } from 'react'
import { ArrowUp, Square } from 'lucide-react'

export default function MessageInput({ onSend, isStreaming }) {
  const [text, setText] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef(null)

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [])

  const handleChange = (e) => {
    setText(e.target.value)
    autoResize()
  }

  const handleKeyDown = (e) => {
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
    <div className="border-t border-gray-800 px-4 py-3 bg-gray-950">
      <div className="flex items-end gap-2 bg-gray-800 rounded-2xl px-4 py-2.5 border border-gray-700 focus-within:border-violet-500 transition-colors">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          placeholder="Message Claude…"
          rows={1}
          disabled={isStreaming}
          className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 resize-none outline-none min-h-[24px] max-h-[200px] leading-6 disabled:opacity-50"
        />
        <button
          onClick={submit}
          disabled={isStreaming || !text.trim()}
          className="shrink-0 w-8 h-8 flex items-center justify-center rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isStreaming ? (
            <Square size={14} className="text-white fill-white" />
          ) : (
            <ArrowUp size={16} className="text-white" />
          )}
        </button>
      </div>
      <p className="text-center text-xs text-gray-600 mt-2">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  )
}
