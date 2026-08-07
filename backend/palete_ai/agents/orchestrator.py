"""Orchestrator: classifies each query and routes it to the menu and/or order agent.

Classification uses an LLM with structured output (a Pydantic schema) rather
than keyword matching. Menu and order agents are nested as subgraphs (no
their own checkpointer) so interrupt()/resume from the order agent's
identifier guard propagates transparently through this graph.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Send
from pydantic import BaseModel, Field

from config import get_logger, llm
from agents.menu_agent import build_menu_agent
from agents.order_agent import build_order_agent
from agents.state import AgentState
from agents.synthesizer import synthesize_node

logger = get_logger("orchestrator")


class RouteDecision(BaseModel):
    """Which specialist agent(s) should handle the user's latest message."""

    menu: bool = Field(
        description="True if the message is about food, menu items, prices, "
        "recommendations, or is a general greeting/small talk."
    )
    order: bool = Field(
        description="True if the message is about order tracking or status "
        "(Order ID, Tracking ID, delivery status, etc.)."
    )


CLASSIFY_PROMPT = """Classify the user's latest message to decide which specialist
agent(s) should handle it: the menu agent (food/menu questions and general
greetings) and/or the order agent (order tracking/status questions). A message
can require both if it touches both topics."""

classifier = llm.with_structured_output(RouteDecision)


def _last_human_text(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def classify(text: str) -> RouteDecision:
    return classifier.invoke([SystemMessage(CLASSIFY_PROMPT), HumanMessage(text)])


def route_query(state: AgentState) -> list[Send]:
    """Conditional edge: classify, then fan out to one or both agents via Send()."""
    text = _last_human_text(state["messages"])
    decision = classify(text)
    logger.info("classified %r -> menu=%s order=%s", text, decision.menu, decision.order)

    destinations = []
    if decision.order:
        destinations.append(Send("order_agent", state))
    if decision.menu or not destinations:
        destinations.append(Send("menu_agent", state))
    return destinations


def build_orchestrator() -> CompiledStateGraph:
    """Wire the classifier-based router to nested menu/order agent subgraphs,
    fanning both back into a synthesizer node that produces one final reply."""
    graph = StateGraph(AgentState)
    graph.add_node("menu_agent", build_menu_agent())
    graph.add_node("order_agent", build_order_agent())
    graph.add_node("synthesize", synthesize_node)
    graph.add_conditional_edges(START, route_query, ["menu_agent", "order_agent"])
    graph.add_edge("menu_agent", "synthesize")
    graph.add_edge("order_agent", "synthesize")
    graph.add_edge("synthesize", END)

    compiled = graph.compile(checkpointer=InMemorySaver())
    logger.info("Orchestrator ready")
    return compiled


_orchestrator: CompiledStateGraph | None = None


def get_orchestrator() -> CompiledStateGraph:
    """Lazily build the orchestrator on first use, then reuse it."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator


def _invoke(payload, thread_id: str) -> dict:
    agent = get_orchestrator()
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(payload, config=config)
    if result.get("__interrupt__"):
        return {"status": "needs_input", "prompt": result["__interrupt__"][0].value}
    return {"status": "done", "answer": result["messages"][-1].content}


def ask(question: str, thread_id: str = "default") -> dict:
    """Start (or continue) a conversation. May return status='needs_input'."""
    return _invoke({"messages": [{"role": "user", "content": question}]}, thread_id)


def resume(user_input: str, thread_id: str = "default") -> dict:
    """Resume a paused conversation (e.g. the order agent asked for an identifier)."""
    return _invoke(Command(resume=user_input), thread_id)


if __name__ == "__main__":
    print("Orchestrator ready. Ask about the menu or your order (Ctrl+C to quit).")
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
