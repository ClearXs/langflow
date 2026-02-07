import pytest

from langflow.services.vector.base import VectorEngineType, VectorMetadata
from langflow.services.vector.config import VectorStoreConfig
from langflow.services.vector.factory import create_vector_store
from langflow.services.vector.milvus_store import MILVUS_AVAILABLE, MilvusVectorStore


def test_milvus_engine_type_exists():
    assert hasattr(VectorEngineType, "MILVUS")


def test_milvus_config_fields():
    config = VectorStoreConfig()
    assert hasattr(config, "milvus_host")
    assert hasattr(config, "milvus_port")
    assert hasattr(config, "milvus_user")
    assert hasattr(config, "milvus_password")
    assert hasattr(config, "milvus_db_name")


def test_milvus_factory_support():
    if not MILVUS_AVAILABLE:
        with pytest.raises(ImportError):
            create_vector_store(VectorEngineType.MILVUS, host="localhost", port=19530)
        return
    store = create_vector_store(VectorEngineType.MILVUS, host="localhost", port=19530)
    assert isinstance(store, MilvusVectorStore)


def test_milvus_schema_compatibility():
    metadata = VectorMetadata(chunk_id=1, document_id=1, space_id=1, chunk_index=0, chunk_type="text")
    assert metadata.chunk_id == 1
    assert metadata.document_id == 1
    assert metadata.space_id == 1


@pytest.mark.skipif(not MILVUS_AVAILABLE, reason="pymilvus not installed")
def test_milvus_store_instantiation():
    store = MilvusVectorStore(host="localhost", port=19530, db_name="test_db")
    assert store.host == "localhost"
    assert store.port == 19530
    assert store.db_name == "test_db"
