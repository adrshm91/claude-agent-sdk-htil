/**
 * Stream a message to the backend and yield parsed SSE events.
 */
export async function streamMessage(
  message: string,
  sessionId: string | null,
  onEvent: (event: any) => void
): Promise<void> {
  const url = sessionId
    ? `/api/v1/messages/stream?resume_session_id=${encodeURIComponent(sessionId)}`
    : '/api/v1/messages/stream'

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`HTTP ${response.status}: ${text}`)
  }

  if (!response.body) {
    throw new Error('Response body is null')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // keep any partial line for next chunk

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const json = line.slice(6).trim()
      if (!json) continue
      try {
        onEvent(JSON.parse(json))
      } catch {
        // skip malformed events
      }
    }
  }
}
