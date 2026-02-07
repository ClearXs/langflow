"""ETL Services for document processing.

This package provides services for document processing:
- Configuration: ETL settings and API keys
- Processors: Document parsing (Unstructured, LlamaCloud, Docling)
- Chunking: Text and code chunking
- Embeddings: Vector embedding generation
- Pipeline: Complete ETL workflow
"""

from langflow.services.etl.chunking import ChunkingService, get_chunking_service
from langflow.services.etl.config import ETLConfig, etl_config
from langflow.services.etl.embeddings import EmbeddingService, get_embedding_service
from langflow.services.etl.pipeline import process_document_etl_pipeline
from langflow.services.etl.processors import (
    DoclingETLProcessor,
    ETLProcessor,
    LlamaCloudETLProcessor,
    UnstructuredETLProcessor,
    get_etl_processor,
    process_document_with_fallback,
)

__all__ = [
    # Configuration
    "ETLConfig",
    "etl_config",
    # Processors
    "ETLProcessor",
    "UnstructuredETLProcessor",
    "LlamaCloudETLProcessor",
    "DoclingETLProcessor",
    "get_etl_processor",
    "process_document_with_fallback",
    # Chunking
    "ChunkingService",
    "get_chunking_service",
    # Embeddings
    "EmbeddingService",
    "get_embedding_service",
    # Pipeline
    "process_document_etl_pipeline",
]
