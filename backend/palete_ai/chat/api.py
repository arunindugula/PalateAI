import asyncio
import base64

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from agents import orchestrator, voice_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


def _text_response(result: dict) -> dict:
    return {
        "status": result["status"],
        "reply": result.get("answer") or result.get("prompt"),
    }


def _voice_response(result: dict) -> dict:
    return {
        "status": result["status"],
        "reply": result.get("answer") or result.get("prompt"),
        "transcript": result["transcript"],
        "audio_base64": base64.b64encode(result["audio"]).decode(),
    }


@router.post("/ask")
def chat_ask(payload: ChatRequest) -> dict:
    """Start (or continue) a text conversation with the orchestrator."""
    return _text_response(orchestrator.ask(payload.message, payload.thread_id))


@router.post("/resume")
def chat_resume(payload: ChatRequest) -> dict:
    """Answer a clarifying question (e.g. the order agent asked for an identifier)."""
    return _text_response(orchestrator.resume(payload.message, payload.thread_id))


@router.post("/voice/ask")
async def chat_voice_ask(audio: UploadFile = File(...), thread_id: str = Form("default")) -> dict:
    """Start (or continue) a voice conversation: transcribe, ask, synthesize the reply."""
    audio_bytes = await audio.read()
    # Run off the event loop: voice_agent makes a blocking HTTP call back to this
    # same server (lookup_order -> /orders/*), which would otherwise deadlock
    # against itself if run directly on the event loop thread.
    result = await asyncio.to_thread(
        voice_agent.voice_ask, audio_bytes, thread_id, audio.filename or "audio.webm"
    )
    return _voice_response(result)


@router.post("/voice/resume")
async def chat_voice_resume(audio: UploadFile = File(...), thread_id: str = Form("default")) -> dict:
    """Answer a clarifying question by voice."""
    audio_bytes = await audio.read()
    result = await asyncio.to_thread(
        voice_agent.voice_resume, audio_bytes, thread_id, audio.filename or "audio.webm"
    )
    return _voice_response(result)
