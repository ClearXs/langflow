from langflow.services.retrieval.hybrid_search import HybridRetrievalService


def test_graph_validation_no_answer():
    assert HybridRetrievalService._validate_graph_answer(None, [], []) is None


def test_graph_validation_no_graph_hits():
    result = HybridRetrievalService._validate_graph_answer("answer", [], [])
    assert result["status"] == "no_graph_hits"
    assert result["matched_doc_ids"] == []


def test_graph_validation_unlinked():
    chunks = [{"document_id": 10}, {"document_id": 11}]
    result = HybridRetrievalService._validate_graph_answer("answer", [1, 2], chunks)
    assert result["status"] == "graph_unlinked"
    assert result["matched_doc_ids"] == []


def test_graph_validation_ok():
    chunks = [{"document_id": 10}, {"document_id": 11}]
    result = HybridRetrievalService._validate_graph_answer("answer", [11, 12], chunks)
    assert result["status"] == "ok"
    assert result["matched_doc_ids"] == [11]
