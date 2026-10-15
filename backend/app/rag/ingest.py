"""Download the employee handbook PDF, chunk it, embed it, and persist to Chroma.

Run with: python -m app.rag.ingest
"""

from __future__ import annotations

import shutil

import httpx
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

COLLECTION_NAME = "employee_handbook"


def download_pdf(force: bool = False) -> str:
    settings = get_settings()
    dest = settings.resolve(settings.pdf_path)
    if dest.exists() and not force:
        print(f"PDF already present at {dest}, skipping download.")
        return str(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {settings.pdf_url} -> {dest}")
    with httpx.stream("GET", settings.pdf_url, follow_redirects=True, timeout=30.0) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return str(dest)


def load_and_chunk(pdf_path: str) -> list[Document]:
    # PyPDFLoader numbers pages from 0; the assessment and the sample dialogue
    # ("Citing Page 4") expect human page numbers, so convert here once and
    # nowhere else downstream has to remember to do it.
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    for doc in raw_docs:
        zero_based_page = doc.metadata.get("page", 0)
        doc.metadata["page"] = zero_based_page + 1
        doc.metadata["source"] = "Employee Handbook"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(raw_docs)


def build_vectorstore(chunks: list[Document], reset: bool = True) -> Chroma:
    settings = get_settings()
    persist_dir = settings.resolve(settings.chroma_dir)

    if reset and persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    store.add_documents(chunks)
    return store


def main() -> None:
    pdf_path = download_pdf()
    chunks = load_and_chunk(pdf_path)
    print(f"Loaded and split into {len(chunks)} chunks.")
    if chunks:
        sample = chunks[0]
        print(f"Sample chunk (page {sample.metadata['page']}):")
        print(sample.page_content[:300])

    store = build_vectorstore(chunks)
    count = store._collection.count()
    print(f"Persisted {count} chunks to Chroma collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
