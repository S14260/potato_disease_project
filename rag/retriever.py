from rag.vectorstore import get_vectorstore


_vectorstore = None


def _get_vs():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def search_knowledge_base(
    query: str,
    doc_type: str = None,
    disease_id: str = None,
    top_k: int = 5,
):
    vs = _get_vs()
    where = {}
    if doc_type:
        where["type"] = doc_type
    if disease_id:
        where["disease_id"] = disease_id

    kwargs = {"query": query, "k": top_k}
    if where:
        kwargs["filter"] = where

    results = vs.similarity_search(**kwargs)
    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in results
    ]
