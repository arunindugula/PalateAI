from config import get_logger
from agents.vector_store import get_vectorstore

from langchain_core.tools import tool

logger = get_logger("tools")

# ═══════════════════════════════════════════════════════════
#  PRODUCT DISCOVERY TOOL
# ═══════════════════════════════════════════════════════════

@tool
def search_product_catalog(query: str) -> str:
    """Search the restaurant menu using semantic search (RAG).

    Args:
        query: natural-language search
    """
    logger.info("search_product_catalog  query=%r", query)
    try:
        store = get_vectorstore()
        docs = store.similarity_search(query, k=10)
        if not docs:
            return "No products found matching your query."
        results = "Found the following products:\n\n"
        for i, doc in enumerate(docs, 1):
            results += f"Product {i}:\n{doc.page_content}\n\n"
        return results
    except Exception as exc:
        logger.exception("Catalog search failed")
        return f"Error searching catalog: {exc}"