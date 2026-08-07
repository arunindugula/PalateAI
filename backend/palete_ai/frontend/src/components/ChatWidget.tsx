import { useRef, useState, type FormEvent } from 'react'
import { chatAsk, chatResume, chatVoiceAsk, chatVoiceResume } from '../api'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import './ChatWidget.css'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
}

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  text: 'Hi! Ask me about the menu, or say something like "check order ORD-1001".',
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [statusText, setStatusText] = useState('')

  const awaitingInputRef = useRef(false)
  const threadIdRef = useRef(crypto.randomUUID())
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const { isRecording, start, stop } = useVoiceRecorder()

  function addMessage(role: ChatMessage['role'], text: string) {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role, text }])
  }

  async function handleSendText(event: FormEvent) {
    event.preventDefault()
    const message = input.trim()
    if (!message || isSending) return

    setInput('')
    addMessage('user', message)
    setIsSending(true)
    setStatusText('Thinking…')
    try {
      const response = awaitingInputRef.current
        ? await chatResume(message, threadIdRef.current)
        : await chatAsk(message, threadIdRef.current)
      awaitingInputRef.current = response.status === 'needs_input'
      addMessage('assistant', response.reply)
    } catch {
      addMessage('assistant', "Sorry, something went wrong reaching the server.")
    } finally {
      setIsSending(false)
      setStatusText('')
    }
  }

  async function handleMicClick() {
    if (isSending) return

    if (!isRecording) {
      setStatusText('Listening…')
      try {
        await start()
      } catch {
        setStatusText('')
        addMessage('assistant', "I couldn't access your microphone.")
      }
      return
    }

    const blob = await stop()
    setIsSending(true)
    setStatusText('Transcribing…')
    try {
      const response = awaitingInputRef.current
        ? await chatVoiceResume(blob, threadIdRef.current)
        : await chatVoiceAsk(blob, threadIdRef.current)
      awaitingInputRef.current = response.status === 'needs_input'
      addMessage('user', response.transcript)
      addMessage('assistant', response.reply)
      if (audioRef.current) {
        audioRef.current.src = `data:audio/mp3;base64,${response.audio_base64}`
        await audioRef.current.play().catch(() => {})
      }
    } catch {
      addMessage('assistant', "Sorry, I couldn't process that recording.")
    } finally {
      setIsSending(false)
      setStatusText('')
    }
  }

  if (!isOpen) {
    return (
      <button className="chat-toggle" onClick={() => setIsOpen(true)} aria-label="Open chat">
        💬
      </button>
    )
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel-header">
        <span>Palete Assistant</span>
        <button onClick={() => setIsOpen(false)} aria-label="Close chat">
          ×
        </button>
      </div>

      <div className="chat-log">
        {messages.map((m) => (
          <div key={m.id} className={`msg msg-${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      <div className="chat-status">{statusText}</div>

      <form className="chat-input-row" onSubmit={handleSendText}>
        <button
          type="button"
          className={`mic-button ${isRecording ? 'recording' : ''}`}
          onClick={handleMicClick}
          aria-label="Record voice message"
        >
          {isRecording ? '⏹' : '🎤'}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={isSending}
        />
        <button type="submit" className="send-button" disabled={isSending} aria-label="Send">
          ➤
        </button>
      </form>

      <audio ref={audioRef} hidden />
    </div>
  )
}
