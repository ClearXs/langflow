import importlib
import pytest

from langflow.api.health_check_router import health_check


class FakeExecResult:
    def first(self):
        return None


class FakeSession:
    async def exec(self, stmt):
        return FakeExecResult()


class FakeChatService:
    async def set_cache(self, key, value):
        return None

    async def get_cache(self, key):
        return "ok"


@pytest.mark.asyncio
async def test_health_check_graph_disabled(monkeypatch):
    import langflow.api.health_check_router as module
    module = importlib.import_module("langflow.api.health_check_router")

    async def _noop():
        return None

    monkeypatch.setattr(module, "get_chat_service", lambda: FakeChatService())
    monkeypatch.setattr(module, "initialize_vector_store", _noop)
    monkeypatch.setattr(module.kg_config, "enabled", False)

    response = await health_check(session=FakeSession())
    assert response.status == "ok"
    assert response.graph == "skipped"
    assert response.vector_store == "ok"


@pytest.mark.asyncio
async def test_health_check_graph_enabled_no_neo4j(monkeypatch):
    import langflow.api.health_check_router as module
    module = importlib.import_module("langflow.api.health_check_router")

    async def _noop():
        return None

    monkeypatch.setattr(module, "get_chat_service", lambda: FakeChatService())
    monkeypatch.setattr(module, "initialize_vector_store", _noop)
    monkeypatch.setattr(module.kg_config, "enabled", True)
    monkeypatch.setattr(module.kg_config, "neo4j_enabled", False)

    response = await health_check(session=FakeSession())
    assert response.status == "ok"
    assert response.graph == "ok"
    assert response.vector_store == "ok"
