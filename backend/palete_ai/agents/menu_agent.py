"""A menu agent that answers questions by searching the restaurant's vector store."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from config import get_logger, llm
from agents.state import AgentState
from agents.tools import search_product_catalog

logger = get_logger("menu_agent")

SYSTEM_PROMPT = """You are a helpful assistant for a restaurant's menu.

Use the search_product_catalog tool to look up menu items before answering
questions about dishes, prices, categories, or recommendations. Only answer
from what the tool returns — don't invent menu items or prices. If the tool
finds nothing relevant, say so instead of guessing."""


def build_menu_agent() -> CompiledStateGraph:
    """Create the menu agent graph: an LLM wired to the catalog search tool."""
    agent = create_react_agent(
        model=llm,
        tools=[search_product_catalog],
        prompt=SYSTEM_PROMPT,
        state_schema=AgentState,
        checkpointer=InMemorySaver(),
    )
    logger.info("Menu agent ready")
    return agent


_menu_agent: CompiledStateGraph | None = None


def get_menu_agent() -> CompiledStateGraph:
    """Lazily build the menu agent on first use, then reuse it."""
    global _menu_agent
    if _menu_agent is None:
        _menu_agent = build_menu_agent()
    return _menu_agent


def ask(question: str, thread_id: str = "default") -> str:
    """Ask the menu agent a question and return its final text reply."""
    agent = get_menu_agent()
    logger.info("Asking menu agent: %s %s", question, thread_id)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    logger.info("Menu agent result: %s %s", result, thread_id)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("Menu agent ready. Ask about the menu (Ctrl+C to quit).")
    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not question:
            continue
        print(f"Agent: {ask(question)}")
