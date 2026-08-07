# Palete AI

An AI assistant for a restaurant: answer menu questions, look up orders, and talk
to it by text or voice. Built with LangGraph (multi-agent orchestration), FastAPI
(backend + REST API), ChromaDB (menu semantic search), and a React/TypeScript
frontend.

## How it works

```
                         ┌─────────────────┐
  text/voice ──────────▶ │   orchestrator   │  classifies the query (LLM,
                         │  (agents/        │  structured output) and routes
                         │  orchestrator.py)│  to one or both agents
                         └───────┬──────────┘
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  menu_agent    │         │  order_agent   │
            │  (ChromaDB     │         │  (regex ID     │
            │  vector search)│         │  extraction +  │
            │                │         │  interrupt())  │
            └───────┬───────┘         └───────┬───────┘
                    └────────────┬────────────┘
                                 ▼
                          ┌─────────────┐
                          │ synthesizer │  merges both replies into
                          │             │  one coherent answer (LLM)
                          └─────────────┘
```

- **`menu_agent`** searches a ChromaDB vector store built from `data/ai_restaurant_menu.json`.
- **`order_agent`** looks up orders from `data/orders.json` via the `/orders/*` REST API.
  If the user's message doesn't contain an Order ID / Tracking ID / email, it pauses
  the graph (`interrupt()`) and asks for one before continuing.
- **`orchestrator`** classifies each message with an LLM (Pydantic structured output)
  and fans out to `menu_agent` and/or `order_agent` in parallel via LangGraph's `Send()`.
- **`synthesizer`** merges the agent(s)' replies into one friendly response — a single
  reply is passed through untouched (no extra LLM call); multiple replies are merged.
- **`voice_agent`** is a thin adapter on top of the orchestrator: transcribes a voice
  clip (OpenAI `gpt-4o-transcribe`), runs it through the same orchestrator as text,
  and synthesizes the reply back to speech (`gpt-4o-mini-tts`).

## Project structure

```
config.py            Shared logger, OpenAI clients (llm, embeddings), env config
main.py              FastAPI app — wires up the /orders and /chat routers

agents/
  vector_store.py    Builds/loads the ChromaDB menu index
  tools.py           LangChain tools: search_product_catalog, lookup_order
  state.py           Shared AgentState (LangGraph) used by every agent
  menu_agent.py       Menu Q&A agent (LangGraph ReAct loop)
  order_agent.py      Order-lookup agent (regex ID extraction + interrupt/resume)
  orchestrator.py     Classifies + routes to menu_agent/order_agent in parallel
  synthesizer.py      Merges multi-agent replies into one answer
  voice_agent.py      Speech-to-text -> orchestrator -> text-to-speech

orders/
  service.py         Order lookup logic (reads data/orders.json)
  api.py              REST endpoints: /orders/order-id, /tracking-id, /email, /phone

chat/
  api.py              REST endpoints: /chat/ask, /resume, /voice/ask, /voice/resume

data/
  ai_restaurant_menu.json   Menu catalog (source for the vector store)
  orders.json                Mock order data

frontend/             React + TypeScript + Vite — restaurant site + chat widget
```

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 18+ and npm (for the frontend)
- An OpenAI API key with access to chat, embeddings, transcription, and TTS models

## Setup

**Backend:**

```bash
uv sync                       # installs all Python dependencies
cp .env.example .env          # then edit .env and set OPENAI_API_KEY=sk-...
```

**Frontend:**

```bash
cd frontend
npm install
```

## Running it

You need three things running together:

**1. Backend API** (from the project root):

```bash
uv run uvicorn main:app --reload
```

Runs on `http://localhost:8000`. Serves both the `/orders/*` REST API and the
`/chat/*` agent API. Note: `order_agent`'s `lookup_order` tool calls this same
API over HTTP, so it must be running for order-related questions to work at all
(menu-only questions don't need it, but leave it running).

**2. Frontend dev server** (from `frontend/`):

```bash
npm run dev
```

Runs on `http://localhost:5173` and proxies `/chat`, `/orders`, `/health` to the
backend (see `frontend/vite.config.ts`) — open this URL in your browser.

The vector store (`chroma_db/`) builds automatically on the first menu question
(embeds all menu items — takes a few seconds) and is reused after that. To force
a rebuild after editing `data/ai_restaurant_menu.json`, run:

```bash
uv run python -c "from agents.vector_store import build_vectorstore; build_vectorstore()"
```

## Testing individual pieces

Each agent has its own CLI REPL, useful for testing without the frontend. Run
these from the project root, with the API server (`uvicorn main:app`) also
running in another terminal:

```bash
uv run python -m agents.menu_agent          # menu Q&A only
uv run python -m agents.order_agent          # order lookup only (with interrupt/resume)
uv run python -m agents.orchestrator         # full routing + synthesis
uv run python -m agents.voice_agent <audio_file> [reply_output.mp3]
```

Or test programmatically:

```python
from agents.orchestrator import ask, resume

r = ask("What soups do you have?", thread_id="test")
print(r)  # {"status": "done", "answer": "..."}

r = ask("Can you check on my order?", thread_id="test2")
print(r)  # {"status": "needs_input", "prompt": "..."}
r = resume("ORD-1001", thread_id="test2")
print(r)  # {"status": "done", "answer": "..."}
```

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/orders/order-id/{id}` | GET | Look up an order by Order ID |
| `/orders/tracking-id/{id}` | GET | Look up an order by Tracking ID |
| `/orders/email/{email}` | GET | Look up an order by email |
| `/orders/phone/{phone}` | GET | Look up an order by phone number |
| `/chat/ask` | POST | `{message, thread_id}` — start/continue a text conversation |
| `/chat/resume` | POST | `{message, thread_id}` — answer a clarifying question |
| `/chat/voice/ask` | POST | multipart `audio` file + `thread_id` — voice conversation |
| `/chat/voice/resume` | POST | multipart `audio` file + `thread_id` — voice follow-up |

`/orders/*` responses never include `Email`/`PhoneNumber` (redacted for privacy),
even when you search by one of those fields. Order/Tracking ID matching ignores
case and punctuation (`ORD1002` and `ORD-1002` match the same order) — useful
since voice transcription often drops hyphens.

`/chat/ask` and `/chat/voice/ask` return `{"status": "needs_input", "reply": "..."}`
when the order agent needs an identifier — call `/chat/resume` (or `/voice/resume`)
with the follow-up to continue that same conversation (same `thread_id`).

## Notes for contributors

- Conversation memory is in-process only (`InMemorySaver`) — it resets when the
  backend restarts, and isn't shared across multiple backend processes/workers.
- `config.py` has zero dependencies on other project modules by design (it's
  imported everywhere) — keep it that way.
- Every agent shares the `AgentState` schema (`agents/state.py`) so new agents
  can be nested into the orchestrator the same way `menu_agent`/`order_agent` are.
