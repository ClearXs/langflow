# Schema Import Guide

After the refactoring, all schemas should be imported using the following patterns:

## Response Schemas (Previously in langflow.schema.holo)

Import from `langflow.schema`:

```python
from langflow.schema import (
    DocumentWithChunksRead,
    PaginatedResponse,
    PermissionInfo,
    PermissionsListResponse,
    SpaceWithStats,
    UserSpaceAccess,
)
```

## Database Models and CRUD Schemas

Import directly from `langflow.services.database.models`:

```python
from langflow.services.database.models import (
    # Space models
    Space, SpaceCreate, SpaceRead, SpaceUpdate,
    
    # Document models
    Document, DocumentCreate, DocumentRead, DocumentUpdate, DocumentType,
    
    # Chunk models
    Chunk, ChunkCreate, ChunkRead,
    
    # Connector models
    Connector, ConnectorCreate, ConnectorRead, ConnectorUpdate, ConnectorType,
    
    # LLM Config models
    LLMConfig, LLMConfigCreate, LLMConfigRead, LLMConfigUpdate, LiteLLMProvider,
    
    # Log models
    Log, LogCreate, LogRead, LogLevel, LogStatus,
    
    # Role models
    Role, RoleCreate, RoleRead, RoleUpdate, Permission, DEFAULT_ROLE_PERMISSIONS,
    
    # Membership models
    SpaceMembership, SpaceMembershipCreate, SpaceMembershipRead,
    
    # Invite models
    SpaceInvite, SpaceInviteCreate, SpaceInviteRead,
    
    # Podcast models
    Podcast, PodcastCreate, PodcastRead, PodcastUpdate,
)
```

## Migration Notes

1. **Removed**: `langflow.schema.holo` module
2. **Created**: `langflow.schema.response` module (imported via `langflow.schema`)
3. **No changes needed**: Database models remain in `langflow.services.database.models`

## Examples

### Example 1: API Response
```python
from langflow.schema import PaginatedResponse, SpaceWithStats
from langflow.services.database.models import SpaceRead

async def list_spaces():
    spaces = await get_spaces()
    return PaginatedResponse(
        items=[SpaceWithStats(space=SpaceRead.from_orm(s), document_count=s.doc_count) 
               for s in spaces],
        total=len(spaces),
        page=1,
        page_size=50
    )
```

### Example 2: Create Document
```python
from langflow.services.database.models import DocumentCreate, DocumentType

doc = DocumentCreate(
    connector_id=1,
    space_id=1,
    user_id="user123",
    title="My Document",
    content="Document content",
    doc_type=DocumentType.FILE,
)
```

### Example 3: Working with LLM Config
```python
from langflow.services.database.models import LLMConfigCreate, LiteLLMProvider

config = LLMConfigCreate(
    search_space_id=1,
    name="GPT-4",
    provider=LiteLLMProvider.OPENAI.value,
    model_name="gpt-4",
    api_key="sk-...",
)
```
