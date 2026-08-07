"""Voice front-end for the orchestrator: speech in, speech out.

Turn-based: transcribe a recorded clip, run it through the same
orchestrator used for text, then synthesize the reply back to audio.
Uses OpenAI's transcription/TTS endpoints directly — LangChain has no
mature audio primitives, so there's nothing to gain from routing through it.
"""

from config import get_logger, openai_client
from agents import orchestrator

logger = get_logger("voice_agent")

TRANSCRIBE_MODEL = "gpt-4o-transcribe"
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "alloy"


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe a recorded voice clip to text."""
    transcript = openai_client.audio.transcriptions.create(
        model=TRANSCRIBE_MODEL,
        file=(filename, audio_bytes),
    )
    logger.info("transcribed %d bytes -> %r", len(audio_bytes), transcript.text)
    return transcript.text


def synthesize(text: str) -> bytes:
    """Synthesize text to speech, returned as MP3 bytes."""
    response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="mp3",
    )
    return response.content


def _voice_reply(result: dict) -> dict:
    """Attach synthesized audio to whichever text field the orchestrator returned."""
    text = result.get("answer") or result.get("prompt")
    result["audio"] = synthesize(text)
    return result


def voice_ask(audio_bytes: bytes, thread_id: str = "default", filename: str = "audio.webm") -> dict:
    """Transcribe a voice clip, start/continue a conversation, and speak the reply.

    Returns {"status", "transcript", "answer"|"prompt", "audio"} — status is
    "needs_input" if the order agent needs an identifier (call voice_resume
    with the follow-up clip), or "done" once there's a final answer.
    """
    transcript = transcribe(audio_bytes, filename)
    result = orchestrator.ask(transcript, thread_id)
    result["transcript"] = transcript
    return _voice_reply(result)


def voice_resume(audio_bytes: bytes, thread_id: str = "default", filename: str = "audio.webm") -> dict:
    """Transcribe a follow-up clip and resume a paused conversation."""
    transcript = transcribe(audio_bytes, filename)
    result = orchestrator.resume(transcript, thread_id)
    result["transcript"] = transcript
    return _voice_reply(result)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agents.voice_agent <audio_file> [reply_output.mp3]")
        raise SystemExit(1)

    with open(sys.argv[1], "rb") as f:
        clip = f.read()

    response = voice_ask(clip, thread_id="cli", filename=sys.argv[1])
    print(f"You said: {response['transcript']}")
    print(f"Agent ({response['status']}): {response.get('answer') or response.get('prompt')}")

    out_path = sys.argv[2] if len(sys.argv) > 2 else "reply.mp3"
    with open(out_path, "wb") as f:
        f.write(response["audio"])
    print(f"Reply audio written to {out_path}")
