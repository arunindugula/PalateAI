"""Builds a Chroma vector store from the restaurant menu JSON data."""

import threading

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
    """Rebuild the persisted ChromaDB collection from the menu catalog.

    Deletes any existing collection first so stale/duplicate items from a
    previous version of the JSON data don't linger.
    """
    Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    ).delete_collection()

    docs = _build_documents(load_menu_items())
    store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_PATH),
    )
    logger.info("Vector store ready  (%d menu items indexed)", len(docs))
    return store


def load_vectorstore() -> Chroma:
    """Open the persisted ChromaDB collection, building it first if missing."""
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    )
    if store._collection.count() == 0:
        logger.info("No existing vector store found, building a new one")
        store = build_vectorstore()
    return store


_product_vectorstore: Chroma | None = None
_vectorstore_lock = threading.Lock()


def get_vectorstore() -> Chroma:
    """Lazily load the vector store on first use, then reuse it.

    Guarded by a lock: agents can run concurrently (e.g. the orchestrator's
    parallel Send() dispatch), and chromadb's PersistentClient isn't safe
    against two threads initialising the same path at once.
    """
    global _product_vectorstore
    if _product_vectorstore is None:
        with _vectorstore_lock:
            if _product_vectorstore is None:
                _product_vectorstore = load_vectorstore()
    return _product_vectorstore
