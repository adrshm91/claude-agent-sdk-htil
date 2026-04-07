import { useAgent } from './hooks/useAgent.ts'
import ChatContainer from './components/ChatContainer.tsx'

export default function App() {
  const { messages, isStreaming, sessionId, meta, status, sendMessage, newSession } = useAgent()

  return (
    <ChatContainer
      messages={messages}
      isStreaming={isStreaming}
      sessionId={sessionId}
      meta={meta}
      status={status}
      onSend={sendMessage}
      onNewSession={newSession}
    />
  )
}
