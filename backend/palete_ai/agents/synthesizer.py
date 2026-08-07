"""Synthesizer: merges menu_agent/order_agent replies into one final answer."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import get_logger, llm
from agents.state import AgentState

logger = get_logger("synthesizer")

SYNTHESIS_PROMPT = """You are the final voice of a restaurant assistant. You'll be
given one or more draft replies, each written by a different specialist agent
(a menu agent and/or an order-tracking agent) answering the same user message.

Merge them into a single, coherent, friendly reply as if one assistant wrote
it from scratch. Preserve every factual detail from each draft (menu items,
prices, order status, etc.) — don't drop information, just make it read as
one natural response instead of two stitched-together answers."""


def synthesize(replies: list[str]) -> str:
    """Merge one or more agent replies into a single friendly response.

    A single reply is just cleaned up (whitespace-trimmed) and returned
    directly, without an LLM call. Multiple replies are merged by the LLM
    into one coherent answer.
    """
    replies = [r.strip() for r in replies if r and r.strip()]
    if not replies:
        return "I'm sorry, I wasn't able to come up with an answer for that."
    if len(replies) == 1:
        return replies[0]

    drafts = "\n\n---\n\n".join(replies)
    response = llm.invoke(
        [
            SystemMessage(SYNTHESIS_PROMPT),
            HumanMessage(f"Draft replies to merge:\n\n{drafts}"),
        ]
    )
    logger.info("synthesized %d replies into one", len(replies))
    return response.content


def _replies_since_last_human(messages: list) -> list[str]:
    """Collect each agent's final AIMessage added after the most recent human message."""
    replies = []
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            break
        if isinstance(message, AIMessage) and message.content:
            replies.append(message.content)
    return list(reversed(replies))


def synthesize_node(state: AgentState) -> dict:
    """Graph node: merge whatever agent replies are in state into one final AIMessage."""
    replies = _replies_since_last_human(state["messages"])
    final_text = synthesize(replies)
    return {"messages": [AIMessage(content=final_text)]}
