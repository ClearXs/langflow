from langflow.services.retrieval.hybrid_search import HybridRetrievalService


def test_build_graph_sources_none_when_no_answer():
    assert HybridRetrievalService._build_graph_sources(None, [1], [2], [3]) is None


def test_build_graph_sources_dedup_and_sort():
    result = HybridRetrievalService._build_graph_sources(
        "answer",
        entity_ids=[3, 1, 3],
        document_ids=[2, 2, 1],
        chunk_ids=[9, 8, 9],
    )

    assert result == {
        "entity_ids": [1, 3],
        "document_ids": [1, 2],
        "chunk_ids": [8, 9],
    }
