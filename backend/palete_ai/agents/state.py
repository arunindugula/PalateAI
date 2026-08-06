"""Shared conversation state used by every agent in the system."""

from typing import Annotated, NotRequired, TypedDict

from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps


class AgentState(TypedDict):
    """Conversation state shared across all agents, keyed by thread_id."""

    messages: Annotated[list, add_messages]
    remaining_steps: NotRequired[RemainingSteps]
