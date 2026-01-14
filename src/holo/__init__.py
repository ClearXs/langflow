"""Holo Knowledge System for Langflow.

This package integrates SurfSense's knowledge management capabilities into Langflow,
providing:

- **Database Models**: Space, Connector, Document, Chunk, Role, etc.
- **Retriever**: Hybrid search (vector + full-text) for documents and chunks
- **Prompts**: Document summarization and LLM prompt templates
- **Connectors**: 15+ integrations with external data sources

Architecture:
- Uses JSON-based embeddings (removed pgvector dependency)
- PostgreSQL for full-text search, SQLite for development
- Space-based multi-tenant isolation
- RBAC with 33 permissions and 4 default roles

## Usage

### Database Models
```python
from langflow.services.database.models import (
    Space, SpaceCreate, SpaceRead,
    Document, DocumentCreate, DocumentRead,
    Chunk, ChunkCreate, ChunkRead,
)
```

### Hybrid Search
```python
from holo.retriever import DocumentHybridSearchRetriever, ChunksHybridSearchRetriever

# Document-level search
doc_retriever = DocumentHybridSearchRetriever(db_session)
results = await doc_retriever.hybrid_search(
    query_text="machine learning",
    top_k=10,
    space_id=1,
)

# Chunk-level search with citations
chunk_retriever = ChunksHybridSearchRetriever(db_session)
results = await chunk_retriever.hybrid_search(
    query_text="neural networks",
    top_k=5,
    space_id=1,
)
```

### Document Summarization
```python
from holo.prompts import SUMMARY_PROMPT_TEMPLATE

summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(document=doc_content)
```

### Connectors
```python
from holo.connectors import GitHubConnector, NotionHistoryConnector

# GitHub integration
github = GitHubConnector(token=github_token)
repos = github.get_user_repositories()

# Notion integration
async with NotionHistoryConnector(token=notion_token) as notion:
    pages = await notion.get_all_pages()
```

## Migration from SurfSense

This package is adapted from SurfSense with the following key changes:

1. **Removed pgvector**: Embeddings stored as JSON (list[float])
2. **Cosine similarity in Python**: Replaces PostgreSQL <=> operator
3. **Langflow integration**: Uses Langflow's database models and services
4. **Namespace**: `app.*` → `langflow.*` or `holo.*`

## Next Steps for Full Integration

1. **API Routes**: Create FastAPI routes for CRUD operations on Spaces, Documents, etc.
2. **Business Logic**: Implement document processing, chunking, embedding generation
3. **RBAC Services**: Add permission checking middleware
4. **Frontend Components**: UI for managing Spaces, Documents, Connectors
5. **Vector Search**: Integrate with Langflow's embedding models
"""

from . import connectors, prompts, retriever

__version__ = "0.1.0"

__all__ = [
    "connectors",
    "prompts",
    "retriever",
]
