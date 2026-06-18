import logging
from pathlib import Path

logger = logging.getLogger(__name__)

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_vectorstore = None

def _get_chroma_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "chroma"

def get_rag_context(query: str, k: int = 3) -> str:
    """Retrieve relevant medical knowledge for a user query."""
    global _vectorstore

    try:
        from langchain_community.vectorstores import Chroma
        from langchain_openai import OpenAIEmbeddings

        from healthguardian.config import get_settings

        settings = get_settings()
        chroma_dir = _get_chroma_dir()

        if not settings.openrouter_api_key:
            return ""

        if not (chroma_dir / "chroma.sqlite3").exists():
            # In production, if no vector DB exists, we do not mock.
            # Return empty context and rely on the LLM's base medical knowledge.
            return ""

        embeddings = OpenAIEmbeddings(
            model="openai/text-embedding-3-small",
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )

        if _vectorstore is None:
            _vectorstore = Chroma(
                persist_directory=str(chroma_dir),
                embedding_function=embeddings,
            )

        results = _vectorstore.similarity_search(query, k=k)
        if not results:
            return ""

        return "\n\n".join(
            f"[{doc.metadata.get('source', 'Medical Guideline')}] {doc.page_content}" for doc in results
        )
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        return ""
