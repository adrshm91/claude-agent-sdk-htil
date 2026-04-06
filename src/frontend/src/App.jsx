import { useAgent } from './hooks/useAgent.js'
import ChatContainer from './components/ChatContainer.jsx'

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
