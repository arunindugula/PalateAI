"""Builds a Chroma vector store from the restaurant menu JSON data."""

from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import get_logger, embeddings
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ai_restaurant_menu.json"
CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
COLLECTION_NAME = "restaurant_menu"

logger = get_logger("vector_store")

def _build_documents(items: list[dict]) -> list[Document]:
    """Convert every catalog entry into a LangChain Document."""
    docs: list[Document] = []
    for p in items:
        content = (
            f"Name: {p['name']}\n"
            f"Category: {p['category']}\n"
            f"Price: ${p['price']}\n"
            f"Description: {p['description']}\n"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "name": p["name"],
                    "category": p["category"],
                    "price": p["price"],
                },
            )
        )
    return docs

def load_menu_items(data_path: Path = DATA_PATH) -> list[dict]:
    with open(data_path) as f:
        return json.load(f)



def build_vectorstore() -> Chroma:
    """Create a persisted ChromaDB collection from the menu catalog."""
    docs = _build_documents(load_menu_items())
    store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_PATH),
    )
    logger.info("Vector store ready  (%d menu items indexed)", len(docs))
    return store


_product_vectorstore: Chroma | None = None


def get_vectorstore() -> Chroma:
    """Lazily build the vector store on first use, then reuse it."""
    global _product_vectorstore
    if _product_vectorstore is None:
        _product_vectorstore = build_vectorstore()
    return _product_vectorstore
