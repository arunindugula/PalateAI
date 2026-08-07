export type ChatStatus = 'needs_input' | 'done'

export interface TextChatResponse {
  status: ChatStatus
  reply: string
}

export interface VoiceChatResponse extends TextChatResponse {
  transcript: string
  audio_base64: string
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Request to ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

async function postAudio(path: string, blob: Blob, threadId: string): Promise<VoiceChatResponse> {
  const form = new FormData()
  form.append('audio', blob, 'recording.webm')
  form.append('thread_id', threadId)
  const res = await fetch(path, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Request to ${path} failed: ${res.status}`)
  return res.json() as Promise<VoiceChatResponse>
}

export function chatAsk(message: string, threadId: string): Promise<TextChatResponse> {
  return postJson('/chat/ask', { message, thread_id: threadId })
}

export function chatResume(message: string, threadId: string): Promise<TextChatResponse> {
  return postJson('/chat/resume', { message, thread_id: threadId })
}

export function chatVoiceAsk(blob: Blob, threadId: string): Promise<VoiceChatResponse> {
  return postAudio('/chat/voice/ask', blob, threadId)
}

export function chatVoiceResume(blob: Blob, threadId: string): Promise<VoiceChatResponse> {
  return postAudio('/chat/voice/resume', blob, threadId)
}
