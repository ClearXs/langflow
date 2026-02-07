import pytest

from langflow.tasks.lightrag_graph_tasks import extract_lightrag_graph_task


def test_lightrag_graph_task_retries_on_failure(monkeypatch):
    async def _raise(document_id, space_id):
        raise ValueError("boom")

    import langflow.tasks.lightrag_graph_tasks as module

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(module, "_extract_lightrag_graph", _raise)
    monkeypatch.setattr(module, "_mark_graph_retry", _noop)

    task_state = {"called": False, "exc": None, "countdown": None}

    def fake_retry(exc, countdown):
        task_state["called"] = True
        task_state["exc"] = exc
        task_state["countdown"] = countdown
        raise RuntimeError("retry-called")

    monkeypatch.setattr(extract_lightrag_graph_task, "retry", fake_retry)

    with pytest.raises(RuntimeError, match="retry-called"):
        extract_lightrag_graph_task._orig_run(document_id=1, space_id=2)

    assert task_state["called"] is True
    assert isinstance(task_state["exc"], ValueError)
    assert task_state["countdown"] == 10
