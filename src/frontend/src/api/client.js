/**
 * Stream a message to the backend and yield parsed SSE events.
 *
 * @param {string} message - User message text
 * @param {string|null} sessionId - Existing session ID to resume, or null to start new
 * @param {(event: object) => void} onEvent - Called for each parsed SSE event
 * @returns {Promise<void>}
 */
export async function streamMessage(message, sessionId, onEvent) {
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

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep any partial line for next chunk

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
