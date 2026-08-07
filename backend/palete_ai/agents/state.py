"""Shared conversation state used by every agent in the system."""

from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps


def _dedup_repeated_human(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Collapse a HumanMessage that repeats the immediately preceding one.

    When the orchestrator fans a query out to multiple agent subgraphs via
    Send(), each nested subgraph re-emits the triggering human message with
    a new id, which add_messages then appends as a duplicate instead of
    merging. With parallel dispatch these duplicates land with the other
    branch's tool-call/answer messages in between, not strictly adjacent —
    so this tracks the most recently seen HumanMessage content while
    scanning forward and skips an immediate repeat of it. AIMessage/
    ToolMessage are left untouched since two agents can legitimately give
    the same reply.
    """
    deduped: list[BaseMessage] = []
    last_human_content = object()  # sentinel that never equals real content
    for message in messages:
        if isinstance(message, HumanMessage):
            if message.content == last_human_content:
                continue
            last_human_content = message.content
        deduped.append(message)
    return deduped


def add_messages_dedup(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    return _dedup_repeated_human(add_messages(left, right))


class AgentState(TypedDict):
    """Conversation state shared across all agents, keyed by thread_id."""

    messages: Annotated[list, add_messages_dedup]
    remaining_steps: NotRequired[RemainingSteps]
