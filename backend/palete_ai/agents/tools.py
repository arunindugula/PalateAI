from urllib.parse import quote

import httpx
from langchain_core.tools import tool

from config import API_BASE_URL, get_logger
from agents.vector_store import get_vectorstore

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


# ═══════════════════════════════════════════════════════════
#  ORDER LOOKUP TOOL
# ═══════════════════════════════════════════════════════════

ORDER_LOOKUP_ENDPOINTS = ["order-id", "tracking-id", "email", "phone"]


def _fetch_order(identifier: str) -> dict | None:
    """Query the orders API, trying each identifier type until one matches."""
    encoded = quote(identifier.strip(), safe="")
    with httpx.Client(base_url=API_BASE_URL, timeout=5.0) as client:
        for endpoint in ORDER_LOOKUP_ENDPOINTS:
            response = client.get(f"/orders/{endpoint}/{encoded}")
            if response.status_code == 200:
                return response.json()
            if response.status_code != 404:
                response.raise_for_status()
    return None


@tool
def lookup_order(identifier: str) -> str:
    """Look up an order by Order ID, Tracking ID, email, or phone number.

    Args:
        identifier: an Order ID (e.g. ORD-1001), Tracking ID (e.g. TRK-88213),
            the customer's email address, or the customer's phone number.
    """
    logger.info("lookup_order  identifier=%r", identifier)
    try:
        order = _fetch_order(identifier)
        if order is None:
            return f"No order found matching '{identifier}'."
        items = ", ".join(f"{item['name']} x{item['quantity']}" for item in order["Items"])
        return (
            f"Order {order['order_id']}\n"
            f"Customer: {order['Customer Name']}\n"
            f"Items: {items}\n"
            f"Status: {order['Status']}\n"
            f"Tracking ID: {order['TrackingId']}"
        )
    except Exception as exc:
        logger.exception("Order lookup failed")
        return f"Error looking up order: {exc}"
