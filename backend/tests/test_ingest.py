from app.rag.retriever import get_retriever, vectorstore_doc_count


def test_vectorstore_has_chunks():
    assert vectorstore_doc_count() > 0


def test_retrieves_performance_review_policy_with_page_number():
    retriever = get_retriever(k=4)
    docs = retriever.invoke("how often are performance reviews conducted")

    assert docs, "expected at least one retrieved chunk"
    joined = " ".join(d.page_content.lower() for d in docs)
    assert "performance review" in joined

    for doc in docs:
        assert isinstance(doc.metadata.get("page"), int)
        assert doc.metadata["page"] >= 1
        assert doc.metadata.get("source") == "Employee Handbook"
