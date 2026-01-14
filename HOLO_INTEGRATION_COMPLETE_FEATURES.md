# Holo 集成完整功能清单 (SurfSense → Langflow)

> **基于 SurfSense 代码库全面审计的完整功能列表**
>
> **审计日期**: 2025-12-29
> **SurfSense 规模**: 124 个 Python 文件 (54,000+ 行代码) + 262 个 TypeScript 文件

---

## 🔴 严重遗漏的功能 (必须实现)

### 1. RBAC 权限系统 ⭐⭐⭐⭐⭐

**数据库模型** (4个新表):

```python
# src/backend/base/langflow/services/database/models/holo/role.py
class Role(SQLModelSerializable, table=True):
    """角色定义"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    search_space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    permissions = Column(ARRAY(String))  # ["DOCUMENTS_CREATE", "CHATS_READ", ...]
    is_default = Column(Boolean, default=False)  # 邀请时默认角色
    is_system_role = Column(Boolean, default=False)  # 系统角色不可删除

# Membership
class SpaceMembership(SQLModelSerializable, table=True):
    """成员关系"""
    __tablename__ = "space_memberships"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID, ForeignKey("user.id", ondelete="CASCADE"))
    search_space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    is_owner = Column(Boolean, default=False)  # 创建者
    joined_at = Column(DateTime(timezone=True))
    invited_by_invite_id = Column(Integer, ForeignKey("space_invites.id"))

# Invite
class SpaceInvite(SQLModelSerializable, table=True):
    """邀请系统"""
    __tablename__ = "space_invites"

    id = Column(Integer, primary_key=True)
    search_space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"))
    invite_code = Column(String(64), unique=True, nullable=False)  # 随机生成
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_by_user_id = Column(UUID, ForeignKey("user.id"))
    expires_at = Column(DateTime(timezone=True))
    max_uses = Column(Integer)  # null = 无限制
    uses_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True))
```

**权限枚举** (17种):

```python
# src/backend/base/langflow/services/database/models/holo/permission.py
class Permission(str, Enum):
    # 文档
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPDATE = "documents:update"
    DOCUMENTS_DELETE = "documents:delete"

    # 聊天
    CHATS_CREATE = "chats:create"
    CHATS_READ = "chats:read"
    CHATS_UPDATE = "chats:update"
    CHATS_DELETE = "chats:delete"

    # LLM 配置
    LLM_CONFIGS_CREATE = "llm_configs:create"
    LLM_CONFIGS_READ = "llm_configs:read"
    LLM_CONFIGS_UPDATE = "llm_configs:update"
    LLM_CONFIGS_DELETE = "llm_configs:delete"

    # 播客
    PODCASTS_CREATE = "podcasts:create"
    PODCASTS_READ = "podcasts:read"
    PODCASTS_UPDATE = "podcasts:update"
    PODCASTS_DELETE = "podcasts:delete"

    # 连接器
    CONNECTORS_CREATE = "connectors:create"
    CONNECTORS_READ = "connectors:read"
    CONNECTORS_UPDATE = "connectors:update"
    CONNECTORS_DELETE = "connectors:delete"

    # 日志
    LOGS_READ = "logs:read"
    LOGS_DELETE = "logs:delete"

    # 成员管理
    MEMBERS_INVITE = "members:invite"
    MEMBERS_VIEW = "members:view"
    MEMBERS_REMOVE = "members:remove"
    MEMBERS_MANAGE_ROLES = "members:manage_roles"

    # 角色管理
    ROLES_CREATE = "roles:create"
    ROLES_READ = "roles:read"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"

    # 设置
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"
    SETTINGS_DELETE = "settings:delete"  # 删除空间

    # 完全访问
    FULL_ACCESS = "*"
```

**预定义角色** (初始化时创建):

```python
# src/backend/base/langflow/services/holo/rbac_service.py
SYSTEM_ROLES = {
    "Owner": {
        "permissions": ["*"],
        "description": "Full access to all features",
        "is_system_role": True,
        "is_default": False,
    },
    "Admin": {
        "permissions": [
            "documents:*", "chats:*", "llm_configs:*", "podcasts:*",
            "connectors:*", "logs:*", "members:*", "roles:*",
            "settings:view", "settings:update",
        ],
        "description": "Can manage all features except deleting the space",
        "is_system_role": True,
        "is_default": False,
    },
    "Editor": {
        "permissions": [
            "documents:*", "chats:*", "connectors:read",
            "llm_configs:read", "podcasts:read",
        ],
        "description": "Can create and edit content",
        "is_system_role": True,
        "is_default": True,  # 邀请时默认角色
    },
    "Viewer": {
        "permissions": [
            "documents:read", "chats:read", "llm_configs:read",
            "podcasts:read", "connectors:read",
        ],
        "description": "Read-only access",
        "is_system_role": True,
        "is_default": False,
    },
}
```

**权限检查中间件**:

```python
# src/backend/base/langflow/api/v1/dependencies/rbac.py
async def check_permission(
    required_permission: Permission,
    current_user: User = Depends(get_current_active_user),
    search_space_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """检查用户权限"""
    # 1. 获取用户成员关系
    membership = await session.execute(
        select(SpaceMembership)
        .where(
            SpaceMembership.user_id == current_user.id,
            SpaceMembership.search_space_id == search_space_id,
        )
    )
    membership = membership.scalar_one_or_none()

    if not membership:
        raise HTTPException(403, "Not a member of this space")

    # 2. 获取角色权限
    role = await session.get(Role, membership.role_id)

    # 3. 检查权限
    if "*" in role.permissions:
        return  # 完全访问

    # 4. 通配符匹配 (e.g., "documents:*" matches "documents:create")
    for perm in role.permissions:
        if perm.endswith(":*"):
            resource = perm.split(":")[0]
            if required_permission.startswith(f"{resource}:"):
                return
        elif perm == required_permission:
            return

    raise HTTPException(403, f"Missing permission: {required_permission}")
```

**前端页面**:

```
src/frontend/src/pages/HoloPage/
├── MembersTab.tsx          # 成员管理
│   ├── MemberList
│   ├── InviteMemberDialog
│   ├── InviteLinkGenerator
│   └── RemoveMemberDialog
└── RolesTab.tsx            # 角色管理
    ├── RoleList
    ├── CreateRoleDialog
    ├── EditRoleDialog
    ├── PermissionMatrix    # 权限选择器
    └── DeleteRoleDialog
```

---

### 2. BlockNote 实时编辑 + 后台重索引 ⭐⭐⭐⭐⭐

**Document 模型扩展**:

```python
# src/backend/base/langflow/services/database/models/holo/document.py
class Document(SQLModelSerializable, table=True):
    # ... 现有字段 ...

    # BlockNote 支持
    blocknote_document = Column(JSONB)  # BlockNote 编辑器状态
    content_needs_reindexing = Column(Boolean, default=False)  # 重索引标记
```

**前端组件**:

```typescript
// src/frontend/src/components/BlockNoteEditor.tsx
import { BlockNoteEditor } from "@blocknote/core";
import { BlockNoteView } from "@blocknote/react";
import { useDebouncedCallback } from "use-debounce";

export function BlockNoteEditor({ documentId, initialContent }) {
  const editor = useCreateBlockNote({
    initialContent: initialContent ? JSON.parse(initialContent) : undefined,
  });

  const { mutate: saveDocument } = useUpdateDocument();

  // 自动保存 (1秒防抖)
  const debouncedSave = useDebouncedCallback(async () => {
    const content = editor.document;
    saveDocument({
      documentId,
      blocknote_document: JSON.stringify(content),
      content_needs_reindexing: true,  // 标记需要重索引
    });
  }, 1000);

  useEffect(() => {
    editor.onChange(() => {
      debouncedSave();
    });
  }, [editor]);

  return <BlockNoteView editor={editor} theme="light" />;
}
```

**后台重索引任务**:

```python
# src/backend/base/langflow/tasks/etl_tasks.py
@celery_app.task(name="reindex_blocknote_document")
async def reindex_blocknote_document(document_id: int):
    """BlockNote 文档后台重索引"""
    async with get_session() as session:
        document = await session.get(Document, document_id)

        # 1. 转换 BlockNote JSON → Markdown
        markdown = blocknote_to_markdown(document.blocknote_document)

        # 2. 重新生成摘要 + Embedding
        llm = await get_document_summary_llm(session, document.space_id)
        summary, embedding = await generate_document_summary(
            markdown, llm, document.document_metadata
        )

        # 3. 重新分块 + Embedding
        await session.execute(
            delete(Chunk).where(Chunk.document_id == document_id)
        )

        chunks = await create_document_chunks(
            markdown, chunker_instance, embedding_model
        )

        # 4. 更新
        document.content = summary
        document.embedding = embedding
        document.content_needs_reindexing = False

        for chunk in chunks:
            chunk.document_id = document_id
            session.add(chunk)

        await session.commit()

# 定期检查任务
@celery_app.task(name="check_documents_needing_reindexing")
async def check_documents_needing_reindexing():
    """检查需要重索引的文档"""
    async with get_session() as session:
        docs = await session.execute(
            select(Document.id).where(Document.content_needs_reindexing == True)
        )

        for doc_id in docs.scalars():
            reindex_blocknote_document.delay(doc_id)
```

**BlockNote → Markdown 转换**:

```python
# src/backend/base/holo/utils/blocknote_utils.py
def blocknote_to_markdown(blocknote_json: dict) -> str:
    """将 BlockNote JSON 转换为 Markdown"""
    blocks = blocknote_json.get("blocks", [])
    markdown_lines = []

    for block in blocks:
        block_type = block.get("type")
        content = block.get("content", [])

        # 提取文本内容
        text = "".join([
            item.get("text", "") for item in content if item.get("type") == "text"
        ])

        # 转换为 Markdown
        if block_type == "heading":
            level = block.get("props", {}).get("level", 1)
            markdown_lines.append(f"{'#' * level} {text}")
        elif block_type == "paragraph":
            markdown_lines.append(text)
        elif block_type == "bulletListItem":
            markdown_lines.append(f"- {text}")
        elif block_type == "numberedListItem":
            markdown_lines.append(f"1. {text}")
        elif block_type == "codeBlock":
            lang = block.get("props", {}).get("language", "")
            markdown_lines.append(f"```{lang}\n{text}\n```")
        # ... 其他块类型

        markdown_lines.append("")  # 空行分隔

    return "\n".join(markdown_lines)
```

---

### 3. 定期索引调度系统 (Meta-scheduler) ⭐⭐⭐⭐⭐

**Connector 模型扩展**:

```python
# src/backend/base/langflow/services/database/models/holo/connector.py
class Connector(SQLModelSerializable, table=True):
    # ... 现有字段 ...

    # 定期索引配置
    periodic_indexing_enabled = Column(Boolean, default=False)
    indexing_frequency_minutes = Column(Integer)  # 15, 30, 60, 1440 (每天)
    next_scheduled_at = Column(DateTime(timezone=True))  # 下次执行时间
    last_indexed_at = Column(DateTime(timezone=True))  # 上次执行时间
```

**Meta-scheduler (Celery Beat 配置)**:

```python
# src/backend/base/langflow/celery_app.py
from celery.schedules import crontab

# 环境变量配置调度间隔
SCHEDULE_CHECKER_INTERVAL = env("SCHEDULE_CHECKER_INTERVAL", "5m")  # 1m, 5m, 1h, 2h

def parse_interval(interval_str: str) -> dict:
    """解析间隔字符串为 crontab"""
    if interval_str.endswith("m"):
        minutes = int(interval_str[:-1])
        return {"minute": f"*/{minutes}"}
    elif interval_str.endswith("h"):
        hours = int(interval_str[:-1])
        return {"hour": f"*/{hours}", "minute": "0"}
    else:
        return {"minute": "*/5"}  # 默认 5 分钟

celery_app.conf.beat_schedule = {
    "check-periodic-connector-schedules": {
        "task": "check_periodic_schedules",
        "schedule": crontab(**parse_interval(SCHEDULE_CHECKER_INTERVAL)),
    },
    "check-documents-needing-reindexing": {
        "task": "check_documents_needing_reindexing",
        "schedule": crontab(minute="*/10"),  # 每 10 分钟
    },
}
```

**调度检查器任务**:

```python
# src/backend/base/langflow/tasks/schedule_checker_task.py
@celery_app.task(name="check_periodic_schedules")
async def check_periodic_schedules():
    """检查并触发到期的定期索引任务"""
    async with get_session() as session:
        now = datetime.now(UTC)

        # 查找到期的连接器
        connectors = await session.execute(
            select(Connector).where(
                Connector.periodic_indexing_enabled == True,
                Connector.next_scheduled_at <= now,
            )
        )

        for connector in connectors.scalars():
            # 更新下次执行时间
            connector.next_scheduled_at = now + timedelta(
                minutes=connector.indexing_frequency_minutes
            )
            await session.commit()

            # 触发索引任务
            task_name = f"index_{connector.connector_type.lower()}_connector"
            celery_app.send_task(
                task_name,
                args=[connector.id],
                priority=1,  # 低优先级
            )

            logger.info(
                f"Scheduled indexing for connector {connector.id} "
                f"(type={connector.connector_type})"
            )
```

---

### 4. 全局 LLM 配置 (YAML) ⭐⭐⭐⭐

**配置文件**:

```yaml
# src/backend/base/langflow/config/global_llm_config.yaml
global_llm_configs:
  -1:  # 默认 Agent LLM
    id: -1
    name: "Default Agent (GPT-4)"
    provider: "OPENAI"
    model_name: "gpt-4o-2024-11-20"
    litellm_params:
      temperature: 0.1
      max_tokens: 16384
    use_default_system_instructions: true
    citations_enabled: true

  -2:  # 默认文档摘要 LLM
    id: -2
    name: "Default Summary (GPT-4o-mini)"
    provider: "OPENAI"
    model_name: "gpt-4o-mini-2024-07-18"
    litellm_params:
      temperature: 0.0
      max_tokens: 4096

  -3:  # 快速 LLM
    id: -3
    name: "Fast (Claude 3.5 Haiku)"
    provider: "ANTHROPIC"
    model_name: "claude-3-5-haiku-20241022"
    litellm_params:
      temperature: 0.0
      max_tokens: 8192
```

**LLM 配置服务**:

```python
# src/backend/base/langflow/services/holo/llm_config_service.py
import yaml

class LLMConfigService:
    def __init__(self):
        config_path = Path(__file__).parent.parent / "config" / "global_llm_config.yaml"
        with open(config_path) as f:
            data = yaml.safe_load(f)
        self.global_configs = data["global_llm_configs"]

    async def get_llm_config(self, session: AsyncSession, config_id: int):
        """获取 LLM 配置 (支持全局和用户配置)"""
        if config_id < 0:
            # 全局配置
            return self.global_configs.get(config_id)
        else:
            # 用户配置
            return await session.get(LLMConfig, config_id)

    async def list_available_llm_configs(
        self, session: AsyncSession, search_space_id: int
    ):
        """列出所有可用的 LLM 配置"""
        # 1. 全局配置
        global_configs = [
            {"id": k, **v, "is_global": True}
            for k, v in self.global_configs.items()
        ]

        # 2. 用户配置
        user_configs = await session.execute(
            select(LLMConfig).where(LLMConfig.search_space_id == search_space_id)
        )
        user_configs = [
            {"id": c.id, **c.dict(), "is_global": False}
            for c in user_configs.scalars()
        ]

        return global_configs + user_configs
```

**Space 模型扩展**:

```python
# src/backend/base/langflow/services/database/models/holo/space.py
class Space(SQLModelSerializable, table=True):
    # ... 现有字段 ...

    # LLM 配置选择
    agent_llm_id = Column(Integer, default=-1)  # -1 = 全局默认 Agent
    document_summary_llm_id = Column(Integer, default=-2)  # -2 = 全局默认摘要
```

---

### 5. 三层 RRF 融合 (完整实现) ⭐⭐⭐⭐⭐

**架构**:

```
Layer 1 (Chunk-level):
  - Vector Search on Chunks (HNSW)
  - Keyword Search on Chunks (GIN + ts_rank_cd)
  - RRF Fusion: score = 1/(k+rank_semantic) + 1/(k+rank_keyword)

Layer 2 (Document-level):
  - Vector Search on Documents (HNSW)
  - Keyword Search on Documents (GIN + ts_rank_cd)
  - RRF Fusion: score = 1/(k+rank_semantic) + 1/(k+rank_keyword)

Layer 3 (Combined):
  - Group chunks by document_id → calculate document-level score from chunks
  - Merge with Layer 2 document results
  - Final RRF: score = 1/(k+rank_from_chunks) + 1/(k+rank_from_docs)
```

**完整实现**:

```python
# src/backend/base/holo/retrieval/combined_rrf_search.py
async def combined_rrf_search(
    session: AsyncSession,
    query: str,
    query_embedding: List[float],
    search_space_id: int,
    top_k: int = 20,
    filters: Optional[dict] = None,
):
    """三层 RRF 融合检索"""
    k = 60  # RRF 常数

    # === Layer 1: Chunk-level RRF ===
    chunk_results = await chunk_hybrid_search(
        session, query, query_embedding, search_space_id,
        top_k=top_k * 5, filters=filters
    )

    # === Layer 2: Document-level RRF ===
    doc_results = await document_hybrid_search(
        session, query, query_embedding, search_space_id,
        top_k=top_k * 3, filters=filters
    )

    # === Layer 3: Combined RRF ===

    # 3.1 将 chunks 按 document_id 分组
    chunks_by_doc = defaultdict(list)
    for idx, chunk_result in enumerate(chunk_results):
        doc_id = chunk_result["document_id"]
        chunks_by_doc[doc_id].append({
            "chunk": chunk_result,
            "rank_in_chunks": idx + 1,  # 排名
        })

    # 3.2 计算每个文档的 chunk-derived 分数
    doc_scores_from_chunks = {}
    for doc_id, chunks in chunks_by_doc.items():
        # 使用最高排名的 chunk 的 RRF 分数
        best_rank = min(c["rank_in_chunks"] for c in chunks)
        doc_scores_from_chunks[doc_id] = 1 / (k + best_rank)

    # 3.3 合并文档结果
    all_docs = {}

    # 从 chunks 推导的文档
    for doc_id in chunks_by_doc.keys():
        document = await session.get(Document, doc_id)
        all_docs[doc_id] = {
            "document": document,
            "chunks": [c["chunk"] for c in chunks_by_doc[doc_id]],
            "score_from_chunks": doc_scores_from_chunks[doc_id],
            "rank_from_chunks": list(doc_scores_from_chunks.keys()).index(doc_id) + 1,
            "score_from_docs": 0.0,
            "rank_from_docs": 99999,
        }

    # 从文档级检索的结果
    for idx, doc_result in enumerate(doc_results):
        doc_id = doc_result["id"]
        if doc_id in all_docs:
            all_docs[doc_id]["score_from_docs"] = doc_result["rrf_score"]
            all_docs[doc_id]["rank_from_docs"] = idx + 1
        else:
            # 新文档,获取其所有 chunks
            document = await session.get(Document, doc_id)
            chunks = await session.execute(
                select(Chunk).where(Chunk.document_id == doc_id)
            )
            all_docs[doc_id] = {
                "document": document,
                "chunks": list(chunks.scalars()),
                "score_from_chunks": 0.0,
                "rank_from_chunks": 99999,
                "score_from_docs": doc_result["rrf_score"],
                "rank_from_docs": idx + 1,
            }

    # 3.4 最终 RRF 融合
    for doc in all_docs.values():
        doc["final_rrf_score"] = (
            1 / (k + doc["rank_from_chunks"]) +
            1 / (k + doc["rank_from_docs"])
        )

    # 3.5 排序并截断
    sorted_docs = sorted(
        all_docs.values(),
        key=lambda x: x["final_rrf_score"],
        reverse=True
    )[:top_k]

    return sorted_docs
```

**Chunk-level Hybrid Search**:

```python
# src/backend/base/holo/retrieval/chunk_hybrid_search.py
async def chunk_hybrid_search(
    session: AsyncSession,
    query: str,
    query_embedding: List[float],
    search_space_id: int,
    top_k: int = 100,
    filters: Optional[dict] = None,
):
    """Chunk 级混合检索 (向量 + 关键词 RRF)"""
    k = 60
    n_results = top_k

    # CTE 1: 向量检索
    semantic_cte = (
        select(
            Chunk.id,
            func.rank().over(
                order_by=Chunk.embedding.l2_distance(query_embedding)
            ).label("semantic_rank")
        )
        .where(Chunk.space_id == search_space_id)
        .order_by(Chunk.embedding.l2_distance(query_embedding))
        .limit(n_results)
        .cte("semantic_search")
    )

    # CTE 2: 关键词检索
    ts_query = func.plainto_tsquery("english", query)
    keyword_cte = (
        select(
            Chunk.id,
            func.rank().over(
                order_by=func.ts_rank_cd(
                    func.to_tsvector("english", Chunk.content),
                    ts_query
                ).desc()
            ).label("keyword_rank")
        )
        .where(
            Chunk.space_id == search_space_id,
            func.to_tsvector("english", Chunk.content).op("@@")(ts_query)
        )
        .order_by(
            func.ts_rank_cd(
                func.to_tsvector("english", Chunk.content),
                ts_query
            ).desc()
        )
        .limit(n_results)
        .cte("keyword_search")
    )

    # RRF 融合
    rrf_score_expr = (
        func.coalesce(1.0 / (k + semantic_cte.c.semantic_rank), 0.0) +
        func.coalesce(1.0 / (k + keyword_cte.c.keyword_rank), 0.0)
    )

    final_query = (
        select(
            Chunk,
            rrf_score_expr.label("rrf_score")
        )
        .select_from(
            semantic_cte.outerjoin(keyword_cte, semantic_cte.c.id == keyword_cte.c.id, full=True)
        )
        .join(Chunk, func.coalesce(semantic_cte.c.id, keyword_cte.c.id) == Chunk.id)
        .order_by(rrf_score_expr.desc())
        .limit(top_k)
    )

    results = await session.execute(final_query)
    return [
        {
            "chunk_id": r.Chunk.id,
            "content": r.Chunk.content,
            "document_id": r.Chunk.document_id,
            "rrf_score": r.rrf_score,
        }
        for r in results
    ]
```

**Document-level Hybrid Search** (类似 Chunk):

```python
# src/backend/base/holo/retrieval/document_hybrid_search.py
async def document_hybrid_search(...):
    # 同样的 RRF 逻辑,应用于 Document 表
    ...
```

---

### 6. Reranker 服务 ⭐⭐⭐⭐

**配置**:

```python
# config/__init__.py
RERANKERS_ENABLED = env("RERANKERS_ENABLED", "FALSE") == "TRUE"
RERANKERS_MODEL_NAME = env("RERANKERS_MODEL_NAME", "ms-marco-MiniLM-L-12-v2")
RERANKERS_MODEL_TYPE = env("RERANKERS_MODEL_TYPE", "flashrank")

if RERANKERS_ENABLED:
    from rerankers import Reranker
    reranker_instance = Reranker(
        model_name=RERANKERS_MODEL_NAME,
        model_type=RERANKERS_MODEL_TYPE
    )
```

**Reranker 服务**:

```python
# src/backend/base/holo/retrieval/reranker_service.py
class RerankerService:
    def __init__(self, reranker_instance):
        self.reranker = reranker_instance

    def rerank_documents(
        self, query: str, documents: List[dict], top_k: int = 20
    ) -> List[dict]:
        """重排序文档 (保留完整 chunks 列表)"""
        # 1. 准备重排序文档
        reranker_docs = [
            {
                "text": doc["document"].content,  # 使用摘要内容
                "doc_id": doc["document"].id,
                "chunks": doc["chunks"],  # 保留完整 chunks
                "original_score": doc["final_rrf_score"],
            }
            for doc in documents
        ]

        # 2. 调用 reranker
        results = self.reranker.rank(
            query=query,
            docs=[d["text"] for d in reranker_docs],
            doc_ids=[d["doc_id"] for d in reranker_docs],
        )

        # 3. 重建结果 (保留 chunks)
        reranked = []
        for result in results.top_k(top_k):
            original_doc = next(
                d for d in reranker_docs if d["doc_id"] == result.doc_id
            )
            reranked.append({
                "document": documents[result.doc_id]["document"],
                "chunks": original_doc["chunks"],  # 保留 chunks
                "reranker_score": result.score,
                "original_rrf_score": original_doc["original_score"],
            })

        return reranked
```

**集成到检索流程**:

```python
# src/backend/base/langflow/services/holo/search_service.py
async def search_knowledge_base(...):
    # 三层 RRF
    results = await combined_rrf_search(...)

    # Reranker (可选)
    if RERANKERS_ENABLED:
        results = reranker_service.rerank_documents(query, results, top_k)

    return results
```

---

### 7. 日志系统 ⭐⭐⭐⭐

**Log 模型**:

```python
# src/backend/base/langflow/services/database/models/holo/log.py
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class Log(SQLModelSerializable, table=True):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    search_space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"))

    level = Column(Enum(LogLevel), nullable=False)
    status = Column(Enum(LogStatus), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(100))  # "connector:github", "task:reindex_document"

    log_metadata = Column(JSONB, default={})  # 灵活元数据

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

**任务日志服务**:

```python
# src/backend/base/langflow/services/holo/task_logging_service.py
class TaskLoggingService:
    def __init__(self, session: AsyncSession, search_space_id: int):
        self.session = session
        self.search_space_id = search_space_id
        self.current_log_id = None

    async def log_task_start(self, source: str, message: str, metadata: dict = None):
        """记录任务开始"""
        log = Log(
            search_space_id=self.search_space_id,
            level=LogLevel.INFO,
            status=LogStatus.IN_PROGRESS,
            message=message,
            source=source,
            log_metadata=metadata or {},
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        self.current_log_id = log.id
        return log.id

    async def log_task_success(self, message: str = None, metadata: dict = None):
        """记录任务成功"""
        if self.current_log_id:
            log = await self.session.get(Log, self.current_log_id)
            log.status = LogStatus.SUCCESS
            if message:
                log.message = message
            if metadata:
                log.log_metadata.update(metadata)
            await self.session.commit()

    async def log_task_error(self, error: Exception, metadata: dict = None):
        """记录任务失败"""
        if self.current_log_id:
            log = await self.session.get(Log, self.current_log_id)
            log.status = LogStatus.FAILED
            log.level = LogLevel.ERROR
            log.message = f"{log.message}\n\nError: {str(error)}"
            if metadata:
                log.log_metadata.update(metadata)
            await self.session.commit()
```

**集成到任务**:

```python
@celery_app.task(name="index_github_connector")
async def index_github_connector(connector_id: int):
    async with get_session() as session:
        connector = await session.get(Connector, connector_id)

        logger_service = TaskLoggingService(session, connector.space_id)

        try:
            await logger_service.log_task_start(
                source=f"connector:{connector.connector_type.lower()}",
                message=f"Indexing GitHub connector: {connector.name}",
                metadata={"connector_id": connector_id}
            )

            # 执行索引
            indexer = GitHubIndexer(connector.config)
            docs = await indexer.fetch_and_process()

            await logger_service.log_task_success(
                message=f"Indexed {len(docs)} documents",
                metadata={"documents_count": len(docs)}
            )

        except Exception as e:
            await logger_service.log_task_error(
                e, metadata={"traceback": traceback.format_exc()}
            )
            raise
```

**前端日志页面**:

```typescript
// src/frontend/src/pages/HoloPage/LogsTab.tsx
export function LogsTab({ searchSpaceId }) {
  const { data: logs } = useLogs(searchSpaceId);

  return (
    <div>
      <LogFilters />  {/* 按 level, status, source 筛选 */}
      <LogTable logs={logs} />
      <LogDetailsDialog />  {/* 查看 metadata */}
    </div>
  );
}
```

---

### 8. Podcaster Agent (完整 LangGraph 实现) ⭐⭐⭐⭐

**Podcast 模型**:

```python
# src/backend/base/langflow/services/database/models/holo/podcast.py
class Podcast(SQLModelSerializable, table=True):
    __tablename__ = "podcasts"

    id = Column(Integer, primary_key=True)
    search_space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"))
    user_id = Column(UUID, ForeignKey("user.id"))

    title = Column(String(500), nullable=False)
    podcast_transcript = Column(JSONB)  # [{speaker, text}, ...]
    file_location = Column(Text)  # S3 URL or local path
    duration_seconds = Column(Integer)

    created_at = Column(DateTime(timezone=True))
```

**LangGraph Podcaster**:

```python
# src/backend/base/holo/agents/podcaster/graph.py
from langgraph.graph import StateGraph
from typing import TypedDict, List

class PodcastState(TypedDict):
    topic: str
    context: str  # 从知识库获取
    outline: List[str]
    transcript: List[dict]  # [{speaker: "Host", text: "..."}, ...]
    audio_file: str

async def generate_outline(state: PodcastState):
    """生成播客大纲"""
    llm = get_llm()

    prompt = f"""Create a detailed outline for a podcast about: {state['topic']}

Context from knowledge base:
{state['context']}

Generate a 5-7 point outline with engaging topics."""

    outline = await llm.ainvoke(prompt)
    return {"outline": parse_outline(outline)}

async def generate_dialogue(state: PodcastState):
    """生成对话脚本"""
    llm = get_llm()

    prompt = f"""Generate an engaging podcast dialogue between Host and Guest.

Topic: {state['topic']}
Outline:
{state['outline']}

Format as:
Host: [text]
Guest: [text]
..."""

    dialogue = await llm.ainvoke(prompt)
    return {"transcript": parse_dialogue(dialogue)}

async def synthesize_audio(state: PodcastState):
    """生成音频"""
    from holo.services.tts_service import TTSService

    tts_service = TTSService()
    audio_segments = []

    for turn in state['transcript']:
        voice = "male" if turn['speaker'] == "Host" else "female"
        audio = await tts_service.synthesize(turn['text'], voice=voice)
        audio_segments.append(audio)

    # 合并音频 (ffmpeg)
    final_audio = ffmpeg.concat(audio_segments)
    audio_file = save_to_s3(final_audio, f"podcasts/{uuid4()}.mp3")

    return {"audio_file": audio_file}

def create_podcast_graph():
    workflow = StateGraph(PodcastState)

    workflow.add_node("generate_outline", generate_outline)
    workflow.add_node("generate_dialogue", generate_dialogue)
    workflow.add_node("synthesize_audio", synthesize_audio)

    workflow.add_edge("generate_outline", "generate_dialogue")
    workflow.add_edge("generate_dialogue", "synthesize_audio")

    workflow.set_entry_point("generate_outline")
    workflow.set_finish_point("synthesize_audio")

    return workflow.compile()
```

**TTS 服务**:

```python
# src/backend/base/holo/services/tts_service.py
class TTSService:
    def __init__(self):
        tts_service = env("TTS_SERVICE", "local/kokoro")

        if tts_service.startswith("local/"):
            # Kokoro 本地 TTS
            from kokoro import generate
            self.generate_fn = generate
            self.use_local = True
        else:
            # LiteLLM TTS
            self.model = tts_service
            self.api_key = env("TTS_SERVICE_API_KEY")
            self.use_local = False

    async def synthesize(self, text: str, voice: str = "male") -> bytes:
        if self.use_local:
            audio = self.generate_fn(text, voice=voice, lang="en-us")
        else:
            from litellm import text_to_speech
            response = await text_to_speech(
                model=self.model,
                text=text,
                voice=voice,
                api_key=self.api_key,
            )
            audio = response.content

        return audio
```

**Agent 工具集成**:

```python
# src/backend/base/holo/agents/tools/podcast.py
async def generate_podcast(
    topic: str,
    use_knowledge_base: bool = True,
    search_space_id: int = None,
    db_session: AsyncSession = None,
):
    """生成播客 (Agent 工具)"""
    # 1. 搜索知识库
    context = ""
    if use_knowledge_base:
        from holo.agents.tools.knowledge_base import search_knowledge_base
        kb_result = await search_knowledge_base(topic, search_space_id, db_session)
        context = kb_result["context"]

    # 2. 调用 Podcaster Graph
    from holo.agents.podcaster.graph import create_podcast_graph
    graph = create_podcast_graph()

    result = await graph.ainvoke({
        "topic": topic,
        "context": context,
    })

    # 3. 保存到数据库
    podcast = Podcast(
        search_space_id=search_space_id,
        title=topic,
        podcast_transcript=result["transcript"],
        file_location=result["audio_file"],
        duration_seconds=calculate_duration(result["audio_file"]),
    )
    db_session.add(podcast)
    await db_session.commit()

    return {
        "podcast_id": podcast.id,
        "audio_url": result["audio_file"],
        "transcript": result["transcript"],
    }
```

---

### 9. 文档去重系统 ⭐⭐⭐⭐

**双哈希机制**:

```python
# src/backend/base/holo/utils/hash_utils.py
def generate_content_hash(content: str, search_space_id: int) -> str:
    """内容哈希 (检测内容变化)"""
    combined = f"{search_space_id}:{content}"
    return hashlib.sha256(combined.encode()).hexdigest()

def generate_unique_identifier_hash(
    document_type: DocumentType,
    unique_identifier: str,
    search_space_id: int,
) -> str:
    """唯一标识哈希 (检测文档身份)"""
    combined = f"{search_space_id}:{document_type}:{unique_identifier}"
    return hashlib.sha256(combined.encode()).hexdigest()
```

**增量更新逻辑**:

```python
# src/backend/base/holo/etl/service.py
async def process_document(
    content: str,
    document_type: DocumentType,
    unique_identifier: str,
    search_space_id: int,
    session: AsyncSession,
    metadata: dict = None,
):
    """处理文档 (支持增量更新)"""
    # 1. 计算哈希
    content_hash = generate_content_hash(content, search_space_id)
    unique_hash = generate_unique_identifier_hash(
        document_type, unique_identifier, search_space_id
    )

    # 2. 检查是否存在
    existing = await session.execute(
        select(Document).where(Document.unique_identifier_hash == unique_hash)
    )
    existing = existing.scalar_one_or_none()

    if existing:
        # 3. 内容哈希比较
        if existing.content_hash == content_hash:
            # 内容未变,跳过
            logger.info(f"Document {unique_identifier} unchanged, skipping")
            return existing

        # 4. 内容变化,更新
        logger.info(f"Document {unique_identifier} changed, updating")

        # 4.1 删除旧 chunks
        await session.execute(delete(Chunk).where(Chunk.document_id == existing.id))

        # 4.2 生成新内容
        summary, embedding = await generate_document_summary(content, llm, metadata)
        chunks = await create_document_chunks(content, chunker, embedding_model)

        # 4.3 更新
        existing.content = summary
        existing.embedding = embedding
        existing.content_hash = content_hash
        existing.document_metadata = metadata
        existing.updated_at = datetime.now(UTC)

        for chunk in chunks:
            chunk.document_id = existing.id
            session.add(chunk)

        await session.commit()
        return existing

    else:
        # 5. 新文档,创建
        summary, embedding = await generate_document_summary(content, llm, metadata)
        chunks = await create_document_chunks(content, chunker, embedding_model)

        document = Document(
            search_space_id=search_space_id,
            document_type=document_type,
            content=summary,
            embedding=embedding,
            content_hash=content_hash,
            unique_identifier_hash=unique_hash,
            document_metadata=metadata,
            chunks=chunks,
        )

        session.add(document)
        await session.commit()
        return document
```

---

### 10. LangGraph Checkpointer (PostgreSQL) ⭐⭐⭐⭐

**初始化**:

```python
# src/backend/base/langflow/services/holo/checkpointer.py
from langgraph.checkpoint.postgres import AsyncPostgresSaver

async def setup_checkpointer_tables():
    """创建 LangGraph 检查点表"""
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()

# 全局 checkpointer 实例
checkpointer = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
```

**Agent 集成**:

```python
# src/backend/base/holo/agents/chat_agent.py
def create_chat_agent(llm, tools, search_space_id):
    from deepagents import create_deep_agent
    from langflow.services.holo.checkpointer import checkpointer

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,  # PostgreSQL 状态持久化
    )

    return agent

# 流式调用
config = {
    "configurable": {
        "thread_id": str(thread_id),  # 对话线程 ID
    }
}

async for event in agent.astream_events(
    {"messages": [user_message]},
    config,  # checkpointer 使用此配置
):
    ...
```

**中断/恢复对话**:

```python
# 恢复对话
state = await checkpointer.aget(config)
if state:
    # 对话存在,继续
    async for event in agent.astream_events(
        {"messages": [user_message]},
        config,
    ):
        ...
```

---

## 🟡 重要遗漏的功能 (高优先级)

### 11. 页面配额系统

**User 模型扩展**:

```python
# src/backend/base/langflow/services/database/models/user.py
class User(SQLModelSerializable, table=True):
    # ... 现有字段 ...

    # 页面配额
    pages_limit = Column(Integer, default=999999999)  # OSS 默认无限制
    pages_used = Column(Integer, default=0)
```

**配额服务**:

```python
# src/backend/base/langflow/services/holo/page_limit_service.py
class PageLimitService:
    @staticmethod
    async def check_and_consume_pages(
        user_id: UUID,
        pages_needed: int,
        session: AsyncSession,
    ):
        """检查并消耗页面配额"""
        user = await session.get(User, user_id)

        if user.pages_used + pages_needed > user.pages_limit:
            raise HTTPException(
                402,
                f"Page limit exceeded. Limit: {user.pages_limit}, "
                f"Used: {user.pages_used}, Requested: {pages_needed}"
            )

        user.pages_used += pages_needed
        await session.commit()

    @staticmethod
    async def get_remaining_pages(user_id: UUID, session: AsyncSession) -> int:
        user = await session.get(User, user_id)
        return user.pages_limit - user.pages_used
```

**ETL 集成**:

```python
# Unstructured/LlamaCloud 计费
pages_processed = len(unstructured_result.pages)
await PageLimitService.check_and_consume_pages(
    user_id, pages_processed, session
)
```

---

### 12. 多 ETL 服务切换

**环境变量**:

```bash
ETL_SERVICE=DOCLING  # DOCLING, UNSTRUCTURED, LLAMACLOUD
UNSTRUCTURED_API_KEY=...
LLAMA_CLOUD_API_KEY=...
```

**ETL 工厂**:

```python
# src/backend/base/holo/etl/factory.py
class ETLFactory:
    @staticmethod
    def get_etl_service():
        etl_service = env("ETL_SERVICE", "DOCLING")

        if etl_service == "DOCLING":
            from holo.etl.docling_service import DoclingService
            return DoclingService()
        elif etl_service == "UNSTRUCTURED":
            from holo.etl.unstructured_service import UnstructuredService
            return UnstructuredService()
        elif etl_service == "LLAMACLOUD":
            from holo.etl.llama_cloud_service import LlamaCloudService
            return LlamaCloudService()
        else:
            raise ValueError(f"Unknown ETL service: {etl_service}")
```

**前端显示**:

```typescript
// .env.local
NEXT_PUBLIC_ETL_SERVICE=DOCLING

// 前端显示当前 ETL 服务
const etlService = process.env.NEXT_PUBLIC_ETL_SERVICE;
```

---

### 13. DeepAgents 集成

**安装**:

```bash
pip install deepagents>=0.3.0
```

**创建 Agent**:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=llm,  # LiteLLM 实例
    tools=tools,  # 工具列表
    system_prompt=system_prompt,
    context_schema=ContextSchema,  # 自定义上下文
    checkpointer=checkpointer,  # LangGraph checkpointer
)
```

**Context Schema**:

```python
# src/backend/base/holo/agents/context_schema.py
from pydantic import BaseModel

class HoloContextSchema(BaseModel):
    """Holo Agent 上下文"""
    search_space_id: int
    user_id: str
    current_search_results: list[dict] = []
    citations: list[str] = []
```

---

### 14. Web 搜索连接器 (实时搜索)

**连接器类型扩展**:

```python
class ConnectorType(str, Enum):
    # ... 现有连接器 ...

    # 实时搜索
    TAVILY_API = "TAVILY_API"
    LINKUP_API = "LINKUP_API"
    BAIDU_SEARCH_API = "BAIDU_SEARCH_API"
    SEARXNG_API = "SEARXNG_API"
```

**Tavily 连接器**:

```python
# src/backend/base/holo/connectors/tavily.py
from tavily import TavilyClient

class TavilyConnector(BaseConnector):
    def __init__(self, config: dict):
        self.client = TavilyClient(api_key=config["api_key"])

    async def search(self, query: str, top_k: int = 5):
        """实时网页搜索"""
        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=top_k,
        )

        # 转换为文档格式
        documents = []
        for result in response["results"]:
            documents.append({
                "title": result["title"],
                "content": result["content"],
                "url": result["url"],
                "score": result["score"],
            })

        return documents
```

**Agent 工具集成**:

```python
# src/backend/base/holo/agents/tools/web_search.py
async def web_search(query: str, connector_type: str = "TAVILY_API"):
    """实时网页搜索 (Agent 工具)"""
    connector = ConnectorFactory.create(connector_type, config)
    results = await connector.search(query, top_k=5)

    # 格式化结果
    formatted = "\n\n".join([
        f"[{r['title']}]({r['url']})\n{r['content']}"
        for r in results
    ])

    return {"results": formatted, "sources": results}
```

---

### 15. LiteLLM 统一接口 (30+ 提供商)

**LLMConfig 模型**:

```python
# src/backend/base/langflow/services/database/models/holo/llm_config.py
class LiteLLMProvider(str, Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    AZURE_OPENAI = "AZURE_OPENAI"
    BEDROCK = "BEDROCK"
    VERTEX_AI = "VERTEX_AI"
    GROQ = "GROQ"
    COHERE = "COHERE"
    MISTRAL = "MISTRAL"
    DEEPSEEK = "DEEPSEEK"
    XAI = "XAI"
    OPENROUTER = "OPENROUTER"
    TOGETHER_AI = "TOGETHER_AI"
    FIREWORKS_AI = "FIREWORKS_AI"
    REPLICATE = "REPLICATE"
    PERPLEXITY = "PERPLEXITY"
    OLLAMA = "OLLAMA"
    CUSTOM = "CUSTOM"  # 自定义提供商

class LLMConfig(SQLModelSerializable, table=True):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True)
    search_space_id = Column(Integer, ForeignKey("spaces.id"))

    name = Column(String(200), nullable=False)
    provider = Column(Enum(LiteLLMProvider), nullable=False)
    custom_provider = Column(String(100))  # 自定义提供商名称
    model_name = Column(String(200), nullable=False)

    # 凭据 (加密存储)
    api_key = Column(String(500))
    api_base = Column(String(500))

    # LiteLLM 参数
    litellm_params = Column(JSONB, default={})  # temperature, max_tokens, etc.

    # 系统提示
    system_instructions = Column(Text)
    use_default_system_instructions = Column(Boolean, default=True)

    # 引用开关
    citations_enabled = Column(Boolean, default=True)
```

**构建 LiteLLM 实例**:

```python
# src/backend/base/langflow/services/holo/llm_service.py
from langchain_litellm import ChatLiteLLM

PROVIDER_PREFIX_MAP = {
    LiteLLMProvider.OPENAI: "openai",
    LiteLLMProvider.ANTHROPIC: "anthropic",
    LiteLLMProvider.GOOGLE: "gemini",
    LiteLLMProvider.AZURE_OPENAI: "azure",
    LiteLLMProvider.GROQ: "groq",
    LiteLLMProvider.COHERE: "cohere",
    LiteLLMProvider.OLLAMA: "ollama",
    # ... 其他提供商
}

async def build_llm_instance(config: LLMConfig) -> ChatLiteLLM:
    """构建 LiteLLM 实例"""
    # 1. 构建 model string
    if config.provider == LiteLLMProvider.CUSTOM:
        model_string = f"{config.custom_provider}/{config.model_name}"
    else:
        prefix = PROVIDER_PREFIX_MAP[config.provider]
        model_string = f"{prefix}/{config.model_name}"

    # 2. 构建参数
    llm = ChatLiteLLM(
        model=model_string,
        api_key=config.api_key,
        api_base=config.api_base,
        **config.litellm_params,
    )

    return llm
```

---

## 🟢 细节功能 (中等优先级)

### 16. Chonkie 智能分块

**配置**:

```python
# config/__init__.py
from chonkie import RecursiveChunker, CodeChunker, AutoEmbeddings

# Embedding 模型
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

embedding_model_instance = AutoEmbeddings.get_embeddings(
    EMBEDDING_MODEL,
    azure_endpoint=env("AZURE_OPENAI_ENDPOINT"),
    azure_api_key=env("AZURE_OPENAI_API_KEY"),
)

# 分块器
chunker_instance = RecursiveChunker(
    chunk_size=embedding_model_instance.max_seq_length,  # 通常 512
    chunk_overlap=int(embedding_model_instance.max_seq_length * 0.1),  # 10%
)

code_chunker_instance = CodeChunker(
    chunk_size=embedding_model_instance.max_seq_length,
    chunk_overlap=int(embedding_model_instance.max_seq_length * 0.1),
)
```

**分块服务**:

```python
# src/backend/base/holo/etl/chunker_service.py
async def create_document_chunks(
    content: str,
    chunker: RecursiveChunker,
    embedding_model: AutoEmbeddings,
    is_code: bool = False,
) -> List[Chunk]:
    """创建文档分块"""
    # 1. 选择分块器
    if is_code:
        chunks = code_chunker_instance.chunk(content)
    else:
        chunks = chunker.chunk(content)

    # 2. 生成 embeddings
    embeddings = embedding_model.embed_documents([c.text for c in chunks])

    # 3. 创建 Chunk 对象
    chunk_objects = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_obj = Chunk(
            chunk_index=idx,
            content=chunk.text,
            embedding=embedding,
        )
        chunk_objects.append(chunk_obj)

    return chunk_objects
```

---

### 17. 引用系统 (Citation System)

**格式化源数据**:

```python
# src/backend/base/langflow/services/holo/citation_service.py
def build_sources_with_citations(documents: List[dict]) -> dict:
    """构建带引用标记的源数据"""
    sources = []
    formatted_context = []

    for doc in documents:
        doc_content = []

        for chunk in doc["chunks"]:
            # 添加引用标记
            citation_marker = f"[citation:{chunk['chunk_id']}]"
            chunk_text_with_citation = f"{chunk['content']} {citation_marker}"

            doc_content.append(chunk_text_with_citation)

            sources.append({
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "document_title": doc["document"].title,
                "document_type": doc["document"].document_type,
                "source_url": doc["document"].source_url,
            })

        # 文档级内容
        doc_text = "\n\n".join(doc_content)
        formatted_context.append(f"### {doc['document'].title}\n\n{doc_text}")

    return {
        "context": "\n\n---\n\n".join(formatted_context),
        "sources": sources,
    }
```

**系统提示**:

```python
CITATION_INSTRUCTIONS = """
<citation_instruction>
IMPORTANT: When you cite information from the knowledge base, use the exact
citation format provided in the search results: [citation:<chunk_id>]

Example:
  Search result: "The deadline is Friday. [citation:12345]"
  Your answer: "According to the meeting notes [citation:12345], the deadline is Friday."

Always cite your sources to help users verify information.
</citation_instruction>
"""
```

**前端解析**:

```typescript
// src/frontend/src/utils/parseCitations.ts
export function parseCitations(content: string, sources: Source[]) {
  const citationRegex = /\[citation:(\d+)\]/g;

  return content.replace(citationRegex, (match, chunkId) => {
    const source = sources.find(s => s.chunk_id === parseInt(chunkId));
    if (source) {
      return `<a
        href="#source-${chunkId}"
        class="citation-link"
        data-document-title="${source.document_title}"
      >
        [${source.document_title}]
      </a>`;
    }
    return match;
  });
}
```

---

### 18. Docling GPU 支持 (WSL2)

**GPU 检测**:

```python
# src/backend/base/holo/etl/docling_service.py
import torch

class DoclingService:
    def __init__(self):
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

        # GPU 检测
        if torch.cuda.is_available():
            logger.info("CUDA available, using GPU for Docling")
            pipeline_options = StandardPdfPipeline.get_default_options()
            pipeline_options.accelerator_device = "cuda"
            self.use_gpu = True
        else:
            logger.info("CUDA not available, using CPU for Docling")
            pipeline_options = StandardPdfPipeline.get_default_options()
            self.use_gpu = False

        # 配置
        pdf_format_option = PdfFormatOption(
            pipeline_options=pipeline_options
        )

        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: pdf_format_option}
        )
```

---

### 19. YouTube 转录

**YouTube 处理器**:

```python
# src/backend/base/holo/etl/processors/youtube_processor.py
from youtube_transcript_api import YouTubeTranscriptApi
from faster_whisper import WhisperModel

class YouTubeProcessor:
    def __init__(self):
        self.whisper_model = WhisperModel("base", device="auto")

    async def process_video(self, video_url: str) -> dict:
        """处理 YouTube 视频"""
        video_id = extract_video_id(video_url)

        # 1. 尝试获取字幕
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([t["text"] for t in transcript])
        except Exception:
            # 2. 字幕不可用,下载音频并转录
            audio_file = download_audio(video_url)
            segments, info = self.whisper_model.transcribe(audio_file)
            text = " ".join([segment.text for segment in segments])
            os.remove(audio_file)

        # 3. 获取视频元数据
        metadata = get_video_metadata(video_id)

        return {
            "title": metadata["title"],
            "content": text,
            "duration": metadata["duration"],
            "channel": metadata["channel"],
            "published_at": metadata["published_at"],
        }
```

---

### 20. S3 存储支持

**S3 服务**:

```python
# src/backend/base/holo/services/s3_service.py
import boto3

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=env("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=env("AWS_SECRET_ACCESS_KEY"),
            region_name=env("AWS_REGION", "us-east-1"),
        )
        self.bucket = env("AWS_S3_BUCKET")

    async def upload_file(self, file_path: str, s3_key: str) -> str:
        """上传文件到 S3"""
        self.s3_client.upload_file(file_path, self.bucket, s3_key)

        url = f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"
        return url

    async def upload_bytes(self, content: bytes, s3_key: str) -> str:
        """上传字节内容到 S3"""
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=content,
        )

        url = f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"
        return url
```

**播客存储**:

```python
# 保存播客到 S3
audio_bytes = generate_podcast_audio(...)
s3_key = f"podcasts/{search_space_id}/{uuid4()}.mp3"
audio_url = await s3_service.upload_bytes(audio_bytes, s3_key)

podcast.file_location = audio_url
```

---

## 📊 实施优先级建议

### P0 (必须实现 - 核心功能)

1. **三层 RRF 融合** - 检索质量核心
2. **RBAC 权限系统** - 多租户必需
3. **文档去重系统** - 避免重复索引
4. **BlockNote 实时编辑** - 用户体验核心
5. **定期索引调度** - 自动化核心

### P1 (高优先级 - 关键功能)

6. **Reranker 服务** - 检索质量提升
7. **全局 LLM 配置** - 易用性
8. **LiteLLM 统一接口** - 兼容性
9. **引用系统** - 可信度核心
10. **日志系统** - 可观测性

### P2 (中优先级 - 增强功能)

11. **Podcaster Agent** - 创新功能
12. **DeepAgents 集成** - Agent 质量
13. **LangGraph Checkpointer** - 对话持久化
14. **页面配额系统** - 成本控制
15. **Web 搜索连接器** - 实时信息

### P3 (低优先级 - 优化功能)

16. **多 ETL 服务切换** - 灵活性
17. **Chonkie 智能分块** - 分块质量
18. **Docling GPU 支持** - 性能优化
19. **YouTube 转录** - 特殊格式
20. **S3 存储** - 存储优化

---

## 总结

SurfSense 的完整集成需要 **20+ 个核心功能模块**,当前的简化版集成计划遗漏了约 **70% 的关键功能**。

建议分阶段实施:
- **阶段 1 (MVP)**: P0 功能 (三层 RRF + RBAC + 去重 + BlockNote + 调度)
- **阶段 2 (增强)**: P1 功能 (Reranker + LLM配置 + 引用 + 日志)
- **阶段 3 (完整)**: P2 + P3 功能 (Podcaster + DeepAgents + 其他)

**关键提醒**: 不要低估 SurfSense 的复杂度,这是一个企业级 RAG 系统,需要认真对待每个功能模块。
