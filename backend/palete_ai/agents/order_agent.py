"""An order-support agent: looks up orders by Order ID, Tracking ID, or email.

If the user's message doesn't contain an identifier, the graph pauses via
interrupt() and asks for one before handing off to a Menu-Agent-style
tool-calling loop that performs the actual lookup.
"""

import re

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from config import get_logger, llm
from agents.state import AgentState
from agents.tools import lookup_order

logger = get_logger("order_agent")

SYSTEM_PROMPT = """You are a helpful customer support assistant for a restaurant's
order tracking system.

Use the lookup_order tool to look up the customer's order by their Order ID,
Tracking ID, or email address. Only answer using what the tool returns — don't
invent order details. If the tool finds nothing, say so and ask the customer
to double-check the identifier."""

IDENTIFIER_PATTERN = re.compile(
    r"(?P<email>[\w.+-]+@[\w-]+\.[A-Za-z]{2,})"
    r"|(?P<order_id>\bORD-?\d+\b)"
    r"|(?P<tracking_id>\b(?:[A-Z]{1,4}\d{2,6}TRK|TRK-?\d{3,8})\b)",
    re.IGNORECASE,
)


def extract_identifier(text: str) -> str | None:
    """Pull an Order ID, Tracking ID, or email address out of free text."""
    match = IDENTIFIER_PATTERN.search(text)
    return match.group(0) if match else None


def _last_human_text(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def ensure_identifier(state: AgentState) -> dict:
    """Guard node: pause the graph and ask the user until an identifier is present."""
    identifier = extract_identifier(_last_human_text(state["messages"]))

    new_messages = []
    while identifier is None:
        user_input = interrupt(
            "I couldn't find an Order ID, Tracking ID, or email in your message. "
            "Could you share one so I can look up your order?"
        )
        new_messages.append({"role": "user", "content": user_input})
        identifier = extract_identifier(user_input)

    return {"messages": new_messages} if new_messages else {}


def build_order_agent() -> CompiledStateGraph:
    """Wire the identifier guard together with a Menu-Agent-style tool-calling loop."""
    tool_loop = create_react_agent(
        model=llm,
        tools=[lookup_order],
        prompt=SYSTEM_PROMPT,
        state_schema=AgentState,
    )

    graph = StateGraph(AgentState)
    graph.add_node("ensure_identifier", ensure_identifier)
    graph.add_node("agent", tool_loop)
    graph.add_edge(START, "ensure_identifier")
    graph.add_edge("ensure_identifier", "agent")
    graph.add_edge("agent", END)

    compiled = graph.compile(checkpointer=InMemorySaver())
    logger.info("Order agent ready")
    return compiled


_order_agent: CompiledStateGraph | None = None


def get_order_agent() -> CompiledStateGraph:
    """Lazily build the order agent on first use, then reuse it."""
    global _order_agent
    if _order_agent is None:
        _order_agent = build_order_agent()
    return _order_agent


def _invoke(payload, thread_id: str) -> dict:
    agent = get_order_agent()
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(payload, config=config)
    if result.get("__interrupt__"):
        return {"status": "needs_input", "prompt": result["__interrupt__"][0].value}
    return {"status": "done", "answer": result["messages"][-1].content}


def ask(question: str, thread_id: str = "default") -> dict:
    """Start (or continue) a conversation. May return status='needs_input'."""
    return _invoke({"messages": [{"role": "user", "content": question}]}, thread_id)


def resume(user_input: str, thread_id: str = "default") -> dict:
    """Resume a paused conversation with the identifier the user just provided."""
    return _invoke(Command(resume=user_input), thread_id)


if __name__ == "__main__":
    print("Order agent ready. Ask about your order (Ctrl+C to quit).")
    try:
        while True:
            question = input("\nYou: ").strip()
            if not question:
                continue

            response = ask(question)
            while response["status"] == "needs_input":
                print(f"Agent: {response['prompt']}")
                user_input = input("You: ").strip()
                response = resume(user_input)
            print(f"Agent: {response['answer']}")
    except (KeyboardInterrupt, EOFError):
        pass
