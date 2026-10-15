from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever

from app.config import get_settings
from app.rag.ingest import COLLECTION_NAME


@lru_cache
def get_vectorstore() -> Chroma:
    settings = get_settings()
    persist_dir = settings.resolve(settings.chroma_dir)
    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )


def get_retriever(k: int = 4) -> VectorStoreRetriever:
    return get_vectorstore().as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": 10})


def vectorstore_doc_count() -> int:
    try:
        return get_vectorstore()._collection.count()
    except Exception:
        return 0
