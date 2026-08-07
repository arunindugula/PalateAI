import { useCallback, useRef, useState } from 'react'

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const resolveRef = useRef<((blob: Blob) => void) | null>(null)

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    chunksRef.current = []

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
      stream.getTracks().forEach((track) => track.stop())
      resolveRef.current?.(blob)
    }

    mediaRecorderRef.current = recorder
    recorder.start()
    setIsRecording(true)
  }, [])

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      resolveRef.current = resolve
      mediaRecorderRef.current?.stop()
      setIsRecording(false)
    })
  }, [])

  return { isRecording, start, stop }
}
