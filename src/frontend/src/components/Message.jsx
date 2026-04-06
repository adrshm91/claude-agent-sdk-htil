import { AlertCircle, ChevronDown, Wrench, ShieldAlert } from 'lucide-react'

export default function Message({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] bg-violet-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }

  if (msg.type === 'text') {
    return (
      <div className="flex justify-start mb-4">
        <div
          className={`max-w-[80%] bg-gray-800 text-gray-100 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm whitespace-pre-wrap${
            msg.streaming ? ' streaming-cursor' : ''
          }`}
        >
          {msg.content}
        </div>
      </div>
    )
  }

  if (msg.type === 'tool_use') {
    return (
      <div className="flex justify-start mb-3">
        <details className="max-w-[80%] w-full bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-sm text-gray-300 hover:text-white select-none list-none">
            <Wrench size={14} className="text-violet-400 shrink-0" />
            <span className="font-mono font-medium">{msg.toolName}</span>
            <ChevronDown size={14} className="ml-auto text-gray-500" />
          </summary>
          <pre className="px-3 pb-3 pt-1 text-xs text-gray-400 overflow-x-auto font-mono">
            {JSON.stringify(msg.toolInput, null, 2)}
          </pre>
        </details>
      </div>
    )
  }

  if (msg.type === 'permission') {
    const p = msg.permission || {}
    return (
      <div className="flex justify-start mb-3">
        <div className="max-w-[80%] border border-amber-500/50 bg-amber-950/30 rounded-xl px-3 py-2.5">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-medium mb-1">
            <ShieldAlert size={14} />
            Permission Request
          </div>
          <p className="text-xs text-amber-200/70">
            Tool <span className="font-mono font-semibold">{p.tool_name ?? 'unknown'}</span> requested — auto-approved by server
          </p>
        </div>
      </div>
    )
  }

  if (msg.type === 'error') {
    return (
      <div className="flex justify-start mb-3">
        <div className="max-w-[80%] border border-red-500/50 bg-red-950/30 rounded-xl px-3 py-2.5">
          <div className="flex items-center gap-2 text-red-400 text-sm font-medium mb-1">
            <AlertCircle size={14} />
            Error
          </div>
          <p className="text-xs text-red-200/70 font-mono">{msg.content}</p>
        </div>
      </div>
    )
  }

  return null
}
