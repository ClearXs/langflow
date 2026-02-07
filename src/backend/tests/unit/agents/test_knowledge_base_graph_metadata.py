import json

import pytest

from langflow.agents.new_chat.tools.knowledge_base import search_knowledge_base_async


class DummyDoc:
    def __init__(self, title: str, file_type: str | None = None):
        self.title = title
        self.file_type = file_type


class DummyChunk:
    def __init__(self, chunk_id: int, document_id: int, content: str, document: DummyDoc):
        self.id = chunk_id
        self.document_id = document_id
        self.content = content
        self.document = document


class DummyConnectorService:
    async def search_youtube(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_extension(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_crawled_urls(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_slack(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_notion(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_github(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_linear(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_jira(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_confluence(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_clickup(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_google_calendar(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_google_gmail(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_discord(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_airtable(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_tavily(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_searxng(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_linkup(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_baidu(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_luma(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")

    async def search_bookstack(self, *args, **kwargs):
        raise AssertionError("unexpected connector call")


def _extract_graph_metadata(output: str) -> dict:
    marker = "<document_type>KNOWLEDGE_GRAPH</document_type>"
    idx = output.find(marker)
    assert idx != -1, "knowledge graph document not found"

    meta_start = output.find("<metadata_json><![CDATA[", idx)
    assert meta_start != -1
    meta_start += len("<metadata_json><![CDATA[")
    meta_end = output.find("]]></metadata_json>", meta_start)
    assert meta_end != -1
    return json.loads(output[meta_start:meta_end])


@pytest.mark.asyncio
async def test_graph_metadata_included_in_kb_response(monkeypatch):
    class DummyRetrievalService:
        async def search(self, *args, **kwargs):
            return {
                "chunks": [
                    DummyChunk(
                        chunk_id=10,
                        document_id=200,
                        content="alpha",
                        document=DummyDoc("Doc A", "pdf"),
                    )
                ],
                "graph_answer": "graph insight",
                "graph_sources": {
                    "entity_ids": [1],
                    "document_ids": [200],
                    "chunk_ids": [10],
                },
                "graph_validation": {
                    "status": "ok",
                    "matched_doc_ids": [200],
                    "chunk_doc_ids": [200],
                },
            }

    def _get_retrieval_service():
        return DummyRetrievalService()

    monkeypatch.setattr(
        "langflow.services.retrieval.get_retrieval_service", _get_retrieval_service
    )

    output = await search_knowledge_base_async(
        query="test",
        space_id=1,
        db_session=None,
        connector_service=DummyConnectorService(),
        connectors_to_search=["FILE"],
        top_k=1,
    )

    metadata = _extract_graph_metadata(output)
    assert metadata["document_type"] == "KNOWLEDGE_GRAPH"
    assert metadata["graph_sources"]["entity_ids"] == [1]
    assert metadata["graph_validation"]["status"] == "ok"
