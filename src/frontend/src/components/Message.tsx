import { AlertCircle, ChevronDown, Wrench, ShieldAlert, Check, X } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Card, CardContent } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Message as MessageType } from '../hooks/useAgent'
import { cn } from '../lib/utils'
import QuestionCard from './QuestionCard'
import { createApiUrl } from '../config/api'

interface MessageProps {
  msg: MessageType
  sessionId: string | null
}

export default function Message({ msg, sessionId }: MessageProps) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <Card className="max-w-[75%] bg-primary border-primary text-primary-foreground">
          <CardContent className="p-4">
            <div className="text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content || ''}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (msg.type === 'text') {
    return (
      <div className="flex justify-start mb-4">
        <Card
          className={cn(
            "max-w-[80%] bg-muted/50 border-muted-foreground/20",
            msg.streaming && "streaming-cursor"
          )}
        >
          <CardContent className="p-4">
            <div className="text-sm prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: ({node, inline, className, children, ...props}) => {
                    return inline ? (
                      <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono" {...props}>
                        {children}
                      </code>
                    ) : (
                      <pre className="bg-muted p-3 rounded-md overflow-x-auto">
                        <code className="text-xs font-mono" {...props}>
                          {children}
                        </code>
                      </pre>
                    )
                  },
                  pre: ({children}) => children
                }}
              >
                {msg.content || ''}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (msg.type === 'tool_use') {
    return (
      <div className="flex justify-start mb-3">
        <Card className="max-w-md w-fit bg-muted/30 border-muted-foreground/20">
          <details className="group">
            <summary className="flex items-center gap-2 p-3 cursor-pointer text-sm text-muted-foreground hover:text-foreground select-none list-none">
              <Wrench size={14} className="text-primary shrink-0" />
              <Badge variant="outline" className="font-mono font-medium">
                {msg.toolName}
              </Badge>
              <ChevronDown size={14} className="ml-auto text-muted-foreground group-open:rotate-180 transition-transform" />
            </summary>
            <CardContent className="pt-0 pb-3 px-3">
              <pre className="text-xs text-muted-foreground overflow-x-auto font-mono bg-muted/50 p-3 rounded-md">
                {JSON.stringify(msg.toolInput, null, 2)}
              </pre>
            </CardContent>
          </details>
        </Card>
      </div>
    )
  }

  if (msg.type === 'permission') {
    const p = msg.permission || {}
    const [responseStatus, setResponseStatus] = useState<'pending' | 'approved' | 'denied' | 'approved_with_suggestions' | 'loading'>('pending')

    // Use session_id from permission data as fallback if sessionId prop is null
    const effectiveSessionId = sessionId || p.session_id

    // Handle AskUserQuestion differently
    if (p.tool_name === 'AskUserQuestion' && p.questions) {
      const handleSubmitAnswers = async (answers: { [key: string]: string }) => {
        const response = await fetch(createApiUrl(`api/v1/permissions/respond?session_id=${effectiveSessionId}`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            request_id: p.request_id,
            allowed: true,
            apply_suggestions: false,
            answers
          })
        })

        if (!response.ok) {
          throw new Error('Failed to submit answers')
        }
      }

      return (
        <QuestionCard
          questions={p.questions}
          onSubmitAnswers={handleSubmitAnswers}
        />
      )
    }

    const handlePermissionResponse = async (allowed: boolean, applysuggestions = false) => {
      setResponseStatus('loading')
      try {
        const response = await fetch(createApiUrl(`api/v1/permissions/respond?session_id=${effectiveSessionId}`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            request_id: p.request_id,
            allowed,
            apply_suggestions: applysuggestions
          })
        })

        if (!response.ok) {
          console.error('Failed to send permission response')
          setResponseStatus('pending') // Reset on error
        } else {
          // Set status based on response
          if (allowed && applysuggestions) {
            setResponseStatus('approved_with_suggestions')
          } else if (allowed) {
            setResponseStatus('approved')
          } else {
            setResponseStatus('denied')
          }
        }
      } catch (error) {
        console.error('Error sending permission response:', error)
        setResponseStatus('pending') // Reset on error
      }
    }

    return (
      <div className="flex justify-start mb-3">
        <Card className="max-w-[80%] border-orange-400/50 bg-orange-950/30 border-2">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 text-orange-400 text-sm font-medium mb-2">
              <ShieldAlert size={14} />
              <Badge variant="outline" className="border-orange-400 text-orange-400">
                PERMISSION REQUIRED
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              TOOL: <Badge variant="outline" className="font-mono text-xs border-orange-400 text-orange-400">
                {p.tool_name ?? 'unknown'}
              </Badge>
            </p>

            {p.tool_input && (
              <div className="mb-3">
                <div className="text-xs text-orange-400 font-semibold mb-1">INPUT:</div>
                <pre className="text-xs text-muted-foreground overflow-x-auto font-mono bg-orange-950/40 rounded p-2">
                  {JSON.stringify(p.tool_input, null, 2)}
                </pre>
              </div>
            )}

            {p.suggestions && p.suggestions.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-orange-400 font-semibold mb-1">SUGGESTIONS:</div>
                <div className="space-y-2">
                  {p.suggestions.map((suggestion: any, idx: number) => (
                    <div key={idx} className="text-xs bg-orange-950/40 rounded p-2">
                      <div className="text-orange-400 font-semibold mb-1">
                        • {typeof suggestion === 'string' ? suggestion : JSON.stringify(suggestion)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {responseStatus === 'pending' ? (
              <div className="flex gap-2">
                <Button
                  onClick={() => handlePermissionResponse(true)}
                  size="sm"
                  className="bg-primary hover:bg-primary/80 text-primary-foreground"
                >
                  Allow
                </Button>
                <Button
                  onClick={() => handlePermissionResponse(false)}
                  size="sm"
                  variant="outline"
                  className="border-muted-foreground/30 text-muted-foreground hover:bg-muted/50"
                >
                  Deny
                </Button>
                {p.suggestions && p.suggestions.length > 0 && (
                  <Button
                    onClick={() => handlePermissionResponse(true, true)}
                    size="sm"
                    className="bg-secondary hover:bg-secondary/80 text-secondary-foreground"
                  >
                    Allow & Apply Suggestions
                  </Button>
                )}
              </div>
            ) : responseStatus === 'loading' ? (
              <div className="flex items-center gap-2 text-orange-400 text-xs">
                <div className="animate-spin rounded-full h-3 w-3 border border-orange-400 border-t-transparent"></div>
                Processing...
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs">
                {responseStatus === 'approved' && (
                  <>
                    <Check size={14} className="text-primary" />
                    <Badge variant="outline" className="border-primary text-primary">
                      Approved
                    </Badge>
                  </>
                )}
                {responseStatus === 'denied' && (
                  <>
                    <X size={14} className="text-muted-foreground" />
                    <Badge variant="outline" className="border-muted-foreground text-muted-foreground">
                      Denied
                    </Badge>
                  </>
                )}
                {responseStatus === 'approved_with_suggestions' && (
                  <>
                    <Check size={14} className="text-secondary" />
                    <Badge variant="outline" className="border-secondary text-secondary">
                      Approved with Suggestions
                    </Badge>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (msg.type === 'error') {
    return (
      <div className="flex justify-start mb-3">
        <Card className="max-w-[80%] border-destructive/30 bg-card border-2">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 text-destructive text-sm font-medium mb-2">
              <AlertCircle size={14} />
              <Badge variant="destructive">
                Error
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground font-mono">{msg.content}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return null
}
