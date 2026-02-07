import pytest

from langflow.tasks.knowledge_graph_tasks import extract_entities_from_document_task


def test_knowledge_graph_task_retries_on_failure(monkeypatch):
    async def _raise(document_id, space_id):
        raise ValueError("boom")

    async def _noop(*args, **kwargs):
        return None

    import langflow.tasks.knowledge_graph_tasks as module

    monkeypatch.setattr(module, "_extract_entities_and_relations", _raise)
    monkeypatch.setattr(module, "_mark_graph_retry", _noop)

    task_state = {"called": False, "exc": None, "countdown": None}

    def fake_retry(exc, countdown):
        task_state["called"] = True
        task_state["exc"] = exc
        task_state["countdown"] = countdown
        raise RuntimeError("retry-called")

    monkeypatch.setattr(extract_entities_from_document_task, "retry", fake_retry)

    with pytest.raises(RuntimeError, match="retry-called"):
        extract_entities_from_document_task._orig_run(document_id=1, space_id=2)

    assert task_state["called"] is True
    assert isinstance(task_state["exc"], ValueError)
    assert task_state["countdown"] == 10
