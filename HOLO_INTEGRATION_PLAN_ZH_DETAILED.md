# Holo 集成详细计划 - 完整中文版

> **完整集成策略**: 将 SurfSense 企业级 RAG 系统完整集成到 Langflow 中作为 "Holo" 知识系统

## 📋 文档修订历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2025-12-29 | **首次发布**:<br>1. 基于完整功能审计创建<br>2. 包含所有 20+ 个核心功能<br>3. 详细的阶段性实施计划<br>4. 每个阶段的具体目标和验收标准 |

---

## 🎯 项目概述

### 项目背景

**用户反馈**: "你做的方案缺少很多的内容 关于 surfsense 的内容，我需要你把他集成过来。你需要在好好的检查是否缺失"

**审计发现**: 原始集成计划遗漏了约 **70% 的 SurfSense 核心功能**。

### SurfSense 规模

- **后端**: 124 个 Python 文件 (54,000+ 行代码)
- **前端**: 262 个 TypeScript 文件
- **架构**: 企业级 RAG 系统，包含 RBAC、实时编辑、元调度器、高级检索

### 集成原则

1. **完整功能对等** - 集成所有 SurfSense 功能，不仅是基础子集
2. **真正融合** - 使用自然命名（Connector、Space、Document），不使用 HoloConnector、HoloSpace 等前缀
3. **对齐 SurfSense 代码库** - 保持相同的架构决策和实现模式

---

## 📊 功能优先级总览

| 优先级 | 功能数量 | 周期 | 理由 |
|--------|---------|------|------|
| **P0** | 5 个功能 | 第 2-5 周 | 系统核心功能，缺少则无法运行 |
| **P1** | 5 个功能 | 第 6-9 周 | 关键质量提升 |
| **P2** | 5 个功能 | 第 10-13 周 | 重要增强功能 |
| **P3** | 5 个功能 | 第 14-16 周 | 性能优化 |

**总计**: 20 个核心功能，16 周（4 个月）

---

## 🗄️ 数据库模型总览

### 核心模型（12 个）

1. **Space** - 知识空间（多租户隔离）
2. **Connector** - 数据源连接器
3. **Document** - 文档元数据
4. **Chunk** - 文档分块（pgvector）
5. **Role** - RBAC 角色
6. **SpaceMembership** - RBAC 成员关系
7. **SpaceInvite** - RBAC 邀请系统
8. **Permission** - RBAC 权限枚举
9. **LLMConfig** - LLM 配置
10. **Log** - 系统日志
11. **Podcast** - 播客
12. **User 扩展** - 页面配额

---

## 🚀 详细实施计划

---

## 阶段 0: 关键准备工作（第 1 周）

### 目标

准备开发环境和基础依赖，确保后续开发顺利进行。

### 详细任务

#### 0.1 Python 依赖安装

**任务描述**: 安装所有后端必需的 Python 包

**具体步骤**:

1. **编辑 `pyproject.toml`**
   ```bash
   cd /Users/jiangwei/Python/langflow
   vim pyproject.toml
   ```

2. **添加依赖项**（在 `[project.dependencies]` 部分）:
   ```toml
   dependencies = [
       # ... 现有 Langflow 依赖 ...

       # === Holo: 向量数据库 (pgvector, 不是 Milvus) ===
       "pgvector>=0.3.6",
       "psycopg[binary,pool]>=3.1.18",

       # === Holo: 文档解析 ===
       "docling>=2.15.0",                   # 主解析器（支持 GPU）
       "unstructured>=0.15.0",              # 备用解析器
       "llama-parse>=0.5.0",                # LlamaCloud 解析器
       "torch>=2.0.0,<2.5.0",               # Docling GPU 必需
       "torchvision>=0.15.0",               # Docling 必需

       # === Holo: 智能分块 ===
       "chonkie[all]>=1.5.0",

       # === Holo: 重排序 ===
       "rerankers[flashrank]>=0.7.1",
       "cohere>=5.0.0",
       "voyageai>=0.2.0",

       # === Holo: 数据源连接器 ===
       "github3.py>=4.0.0",                 # GitHub
       "slack-sdk>=3.27.0",                 # Slack
       "notion-client>=2.2.0",              # Notion
       "jira>=3.8.0",                       # Jira
       "python-gitlab>=4.4.0",              # GitLab
       "discord.py>=2.3.0",                 # Discord
       "atlassian-python-api>=3.41.0",      # Confluence
       "google-api-python-client>=2.130.0", # Google Drive
       "dropbox>=12.0.0",                   # Dropbox
       "msal>=1.28.0",                      # Microsoft OneDrive
       "tavily-python>=0.3.0",              # Tavily 网页搜索
       "youtube-transcript-api>=0.6.0",     # YouTube 转录
       "faster-whisper>=1.0.0",             # Whisper 音频转录

       # === Holo: Agent 框架 ===
       "deepagents>=0.3.0",
       "langgraph>=1.0.5",
       "langgraph-checkpoint-postgres>=3.0.2",

       # === Holo: LLM 接口 ===
       "litellm>=1.80.10",                  # 30+ LLM 提供商

       # === Holo: 工具 ===
       "auto-embeddings>=1.0.0",
       "tiktoken>=0.7.0",
       "boto3>=1.34.0",                     # S3 存储
       "pyyaml>=6.0.1",                     # YAML 配置
   ]
   ```

3. **安装依赖**:
   ```bash
   uv sync
   ```

4. **验证安装**:
   ```bash
   uv run python -c "import pgvector; import litellm; import deepagents; print('依赖安装成功')"
   ```

**预期输出**: "依赖安装成功"

**耗时**: 2-3 小时（取决于网络速度）

---

#### 0.2 前端依赖安装

**任务描述**: 安装所有前端必需的 Node.js 包

**具体步骤**:

1. **编辑 `package.json`**:
   ```bash
   cd src/frontend
   vim package.json
   ```

2. **添加依赖项**（在 `dependencies` 部分）:
   ```json
   {
     "dependencies": {
       // ... 现有 Langflow 依赖 ...

       // Holo: 实时编辑
       "@blocknote/core": "^0.15.0",
       "@blocknote/react": "^0.15.0",

       // Holo: 聊天 UI
       "@assistant-ui/react": "^0.5.0",

       // Holo: 数据获取
       "@tanstack/react-query": "^5.0.0",

       // Holo: 表单处理
       "react-hook-form": "^7.51.0",
       "zod": "^3.22.0",
       "@hookform/resolvers": "^3.3.4",

       // Holo: Markdown 和代码
       "react-markdown": "^9.0.0",
       "remark-gfm": "^4.0.0",
       "react-syntax-highlighter": "^15.5.0",

       // Holo: 日期处理
       "date-fns": "^3.3.0",

       // Holo: 虚拟滚动
       "@tanstack/react-virtual": "^3.2.0",

       // Holo: 图表
       "recharts": "^2.12.0"
     }
   }
   ```

3. **安装依赖**:
   ```bash
   npm install
   ```

4. **验证安装**:
   ```bash
   npm list @blocknote/react @tanstack/react-query
   ```

**预期输出**: 显示已安装的包版本

**耗时**: 1-2 小时

---

#### 0.3 配置 PostgreSQL + pgvector

**任务描述**: 启用 PostgreSQL 的 pgvector 扩展

**具体步骤**:

1. **连接到 PostgreSQL**:
   ```bash
   # 使用 Langflow 的数据库连接
   psql -U langflow -d langflow
   ```

2. **启用 pgvector 扩展**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **验证扩展已启用**:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

4. **测试向量操作**:
   ```sql
   -- 创建测试表
   CREATE TABLE test_vectors (
       id SERIAL PRIMARY KEY,
       embedding vector(1536)
   );

   -- 插入测试数据
   INSERT INTO test_vectors (embedding)
   VALUES (array_fill(0.1, ARRAY[1536])::vector);

   -- 查询测试
   SELECT * FROM test_vectors LIMIT 1;

   -- 清理测试表
   DROP TABLE test_vectors;
   ```

**预期输出**: 查询返回 1 行数据

**耗时**: 30 分钟

---

#### 0.4 创建数据库迁移

**任务描述**: 为所有 Holo 模型创建 Alembic 迁移脚本

**具体步骤**:

1. **创建迁移脚本**:
   ```bash
   cd src/backend/base/langflow
   uv run alembic revision -m "add_holo_models_complete"
   ```

2. **编辑生成的迁移文件**（位于 `alembic/versions/`）:

   **升级函数** (`upgrade()`):
   ```python
   def upgrade() -> None:
       # === 1. Space 表 ===
       op.create_table(
           'spaces',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
           sa.Column('name', sa.String(length=255), nullable=False),
           sa.Column('description', sa.Text(), nullable=True),
           sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
           sa.Column('agent_llm_id', sa.Integer(), nullable=True, server_default='-1'),
           sa.Column('document_summary_llm_id', sa.Integer(), nullable=True, server_default='-2'),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
           sa.PrimaryKeyConstraint('id')
       )

       # === 2. Connector 表 ===
       op.create_table(
           'connectors',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('space_id', sa.Integer(), nullable=False),
           sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
           sa.Column('name', sa.String(length=255), nullable=False),
           sa.Column('connector_type', sa.Enum(
               'GITHUB', 'SLACK', 'NOTION', 'JIRA', 'GITLAB', 'DISCORD',
               'CONFLUENCE', 'LINEAR', 'ASANA', 'GOOGLE_DRIVE', 'DROPBOX',
               'ONEDRIVE', 'ZENDESK', 'SALESFORCE', 'HUBSPOT',
               'TAVILY_API', 'LINKUP_API', 'BAIDU_SEARCH_API', 'SEARXNG_API',
               name='connectortype'
           ), nullable=False),
           sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
           sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
           sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('periodic_indexing_enabled', sa.Boolean(), nullable=True, server_default='false'),
           sa.Column('indexing_frequency_minutes', sa.Integer(), nullable=True),
           sa.Column('next_scheduled_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
           sa.PrimaryKeyConstraint('id')
       )

       # === 3. Document 表 ===
       op.create_table(
           'documents',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('space_id', sa.Integer(), nullable=False),
           sa.Column('connector_id', sa.Integer(), nullable=True),
           sa.Column('document_id', sa.String(length=256), nullable=False),
           sa.Column('title', sa.String(length=500), nullable=True),
           sa.Column('document_type', sa.Enum(
               'GITHUB', 'SLACK', 'NOTION', 'JIRA', 'DISCORD', 'CONFLUENCE',
               'LINEAR', 'MANUAL_UPLOAD', 'WEB_CRAWL', 'YOUTUBE',
               name='documenttype'
           ), nullable=False),
           sa.Column('source_url', sa.String(length=1024), nullable=True),
           sa.Column('content', sa.Text(), nullable=True),
           sa.Column('embedding', postgresql.VECTOR(1536), nullable=True),
           sa.Column('content_hash', sa.String(length=64), nullable=True),
           sa.Column('unique_identifier_hash', sa.String(length=64), nullable=False),
           sa.Column('blocknote_document', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
           sa.Column('content_needs_reindexing', sa.Boolean(), nullable=True, server_default='false'),
           sa.Column('chunk_count', sa.Integer(), nullable=True, server_default='0'),
           sa.Column('total_tokens', sa.Integer(), nullable=True, server_default='0'),
           sa.Column('document_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id'),
           sa.UniqueConstraint('document_id'),
           sa.UniqueConstraint('unique_identifier_hash')
       )
       op.create_index('ix_documents_content_hash', 'documents', ['content_hash'])
       op.create_index('ix_documents_unique_identifier_hash', 'documents', ['unique_identifier_hash'])

       # === 4. Chunk 表 ===
       op.create_table(
           'chunks',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('document_id', sa.Integer(), nullable=False),
           sa.Column('space_id', sa.Integer(), nullable=False),
           sa.Column('chunk_id', sa.String(length=256), nullable=False),
           sa.Column('chunk_index', sa.Integer(), nullable=False),
           sa.Column('content', sa.Text(), nullable=False),
           sa.Column('embedding', postgresql.VECTOR(1536), nullable=True),
           sa.Column('source_type', sa.String(length=64), nullable=True),
           sa.Column('source_url', sa.String(length=1024), nullable=True),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id'),
           sa.UniqueConstraint('chunk_id')
       )

       # === 5. Role 表 (RBAC) ===
       op.create_table(
           'roles',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=False),
           sa.Column('name', sa.String(length=100), nullable=False),
           sa.Column('description', sa.Text(), nullable=True),
           sa.Column('permissions', postgresql.ARRAY(sa.String()), nullable=True),
           sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
           sa.Column('is_system_role', sa.Boolean(), nullable=True, server_default='false'),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id')
       )

       # === 6. SpaceMembership 表 (RBAC) ===
       op.create_table(
           'space_memberships',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=False),
           sa.Column('role_id', sa.Integer(), nullable=False),
           sa.Column('is_owner', sa.Boolean(), nullable=True, server_default='false'),
           sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('invited_by_invite_id', sa.Integer(), nullable=True),
           sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
           sa.ForeignKeyConstraint(['invited_by_invite_id'], ['space_invites.id'], ),
           sa.PrimaryKeyConstraint('id')
       )

       # === 7. SpaceInvite 表 (RBAC) ===
       op.create_table(
           'space_invites',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=False),
           sa.Column('role_id', sa.Integer(), nullable=False),
           sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
           sa.Column('invite_code', sa.String(length=64), nullable=False),
           sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('max_uses', sa.Integer(), nullable=True),
           sa.Column('uses_count', sa.Integer(), nullable=True, server_default='0'),
           sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
           sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id'], ),
           sa.PrimaryKeyConstraint('id'),
           sa.UniqueConstraint('invite_code')
       )

       # === 8. LLMConfig 表 ===
       op.create_table(
           'llm_configs',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=True),
           sa.Column('name', sa.String(length=200), nullable=False),
           sa.Column('provider', sa.Enum(
               'OPENAI', 'ANTHROPIC', 'GOOGLE', 'AZURE_OPENAI', 'BEDROCK',
               'VERTEX_AI', 'GROQ', 'COHERE', 'MISTRAL', 'DEEPSEEK', 'XAI',
               'OPENROUTER', 'TOGETHER_AI', 'FIREWORKS_AI', 'REPLICATE',
               'PERPLEXITY', 'OLLAMA', 'CUSTOM',
               name='litellmprovider'
           ), nullable=False),
           sa.Column('custom_provider', sa.String(length=100), nullable=True),
           sa.Column('model_name', sa.String(length=200), nullable=False),
           sa.Column('api_key', sa.String(length=500), nullable=True),
           sa.Column('api_base', sa.String(length=500), nullable=True),
           sa.Column('litellm_params', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
           sa.Column('system_instructions', sa.Text(), nullable=True),
           sa.Column('use_default_system_instructions', sa.Boolean(), nullable=True, server_default='true'),
           sa.Column('citations_enabled', sa.Boolean(), nullable=True, server_default='true'),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id')
       )

       # === 9. Log 表 ===
       op.create_table(
           'logs',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=False),
           sa.Column('level', sa.Enum(
               'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
               name='loglevel'
           ), nullable=False),
           sa.Column('status', sa.Enum(
               'IN_PROGRESS', 'SUCCESS', 'FAILED',
               name='logstatus'
           ), nullable=False),
           sa.Column('message', sa.Text(), nullable=False),
           sa.Column('source', sa.String(length=100), nullable=True),
           sa.Column('log_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id')
       )

       # === 10. Podcast 表 ===
       op.create_table(
           'podcasts',
           sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
           sa.Column('search_space_id', sa.Integer(), nullable=False),
           sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
           sa.Column('title', sa.String(length=500), nullable=False),
           sa.Column('podcast_transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
           sa.Column('file_location', sa.Text(), nullable=True),
           sa.Column('duration_seconds', sa.Integer(), nullable=True),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
           sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
           sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
           sa.PrimaryKeyConstraint('id')
       )

       # === 11. User 表扩展 (页面配额) ===
       op.add_column('user', sa.Column('pages_limit', sa.Integer(), nullable=True, server_default='999999999'))
       op.add_column('user', sa.Column('pages_used', sa.Integer(), nullable=True, server_default='0'))

       # === 索引优化 ===
       # 向量索引 (HNSW)
       op.execute('CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_l2_ops)')
       op.execute('CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_l2_ops)')

       # GIN 索引用于全文搜索
       op.execute('CREATE INDEX ix_documents_content_gin ON documents USING gin(to_tsvector(\'english\', content))')
       op.execute('CREATE INDEX ix_chunks_content_gin ON chunks USING gin(to_tsvector(\'english\', content))')


   def downgrade() -> None:
       # 删除索引
       op.execute('DROP INDEX IF EXISTS ix_chunks_content_gin')
       op.execute('DROP INDEX IF EXISTS ix_documents_content_gin')
       op.execute('DROP INDEX IF EXISTS ix_chunks_embedding')
       op.execute('DROP INDEX IF EXISTS ix_documents_embedding')

       # 删除 User 扩展列
       op.drop_column('user', 'pages_used')
       op.drop_column('user', 'pages_limit')

       # 删除表（反向顺序）
       op.drop_table('podcasts')
       op.drop_table('logs')
       op.drop_table('llm_configs')
       op.drop_table('space_invites')
       op.drop_table('space_memberships')
       op.drop_table('roles')
       op.drop_table('chunks')
       op.drop_index('ix_documents_unique_identifier_hash')
       op.drop_index('ix_documents_content_hash')
       op.drop_table('documents')
       op.drop_table('connectors')
       op.drop_table('spaces')

       # 删除枚举类型
       sa.Enum(name='logstatus').drop(op.get_bind())
       sa.Enum(name='loglevel').drop(op.get_bind())
       sa.Enum(name='litellmprovider').drop(op.get_bind())
       sa.Enum(name='documenttype').drop(op.get_bind())
       sa.Enum(name='connectortype').drop(op.get_bind())
   ```

3. **执行迁移**:
   ```bash
   uv run alembic upgrade head
   ```

4. **验证迁移**:
   ```bash
   psql -U langflow -d langflow -c "\dt" | grep -E "(spaces|connectors|documents|chunks|roles|space_memberships|space_invites|llm_configs|logs|podcasts)"
   ```

**预期输出**: 显示所有 10 个新表

**耗时**: 2-3 小时

---

### 阶段 0 验收标准

- [ ] 所有 Python 依赖安装成功（无冲突）
- [ ] 所有前端依赖安装成功
- [ ] PostgreSQL pgvector 扩展已启用
- [ ] 数据库迁移成功执行
- [ ] PostgreSQL 包含所有 10 个 Holo 表
- [ ] 向量索引（HNSW）已创建
- [ ] GIN 全文搜索索引已创建

**完成标志**: 运行 `psql -U langflow -d langflow -c "\d documents"` 显示表结构包含 `embedding vector(1536)` 字段

---

## 阶段 1: P0 功能 - 核心功能（第 2-5 周）

### 总体目标

实现系统运行所必需的核心功能，缺少这些功能系统无法正常工作。

---

### P0.1: 三层 RRF 融合检索（第 2 周）

#### 功能描述

实现 SurfSense 的核心检索算法：三层倒数排名融合（Reciprocal Rank Fusion）

**架构**:
```
第一层 (Chunk 级别):
  - 向量搜索 (pgvector HNSW)
  - 关键词搜索 (PostgreSQL GIN + ts_rank_cd)
  - RRF 融合

第二层 (Document 级别):
  - 向量搜索 (pgvector HNSW)
  - 关键词搜索 (PostgreSQL GIN + ts_rank_cd)
  - RRF 融合

第三层 (组合):
  - 将 chunks 按 document_id 分组
  - 与第二层的 document 结果合并
  - 最终 RRF 融合
```

#### 详细任务

**任务 1.1: 创建 Chunk 级混合搜索**

**文件**: `src/backend/base/holo/retrieval/chunk_hybrid_search.py`

**实现步骤**:

1. **创建文件**:
   ```bash
   mkdir -p src/backend/base/holo/retrieval
   touch src/backend/base/holo/retrieval/__init__.py
   touch src/backend/base/holo/retrieval/chunk_hybrid_search.py
   ```

2. **实现代码**:
   ```python
   # src/backend/base/holo/retrieval/chunk_hybrid_search.py

   from typing import List, Optional, Dict, Any
   from sqlalchemy import select, func
   from sqlalchemy.ext.asyncio import AsyncSession
   from langflow.services.database.models.holo.chunk import Chunk


   async def chunk_hybrid_search(
       session: AsyncSession,
       query: str,
       query_embedding: List[float],
       search_space_id: int,
       top_k: int = 100,
       filters: Optional[dict] = None,
   ) -> List[Dict[str, Any]]:
       """Chunk 级混合检索（向量 + 关键词 RRF）

       Args:
           session: 数据库会话
           query: 查询文本
           query_embedding: 查询向量
           search_space_id: 空间 ID（多租户隔离）
           top_k: 返回结果数量
           filters: 额外过滤条件

       Returns:
           混合检索结果列表，包含 RRF 分数
       """
       k = 60  # RRF 常数
       n_results = top_k

       # === CTE 1: 向量检索 ===
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

       # === CTE 2: 关键词检索 ===
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

       # === RRF 融合 ===
       rrf_score_expr = (
           func.coalesce(1.0 / (k + semantic_cte.c.semantic_rank), 0.0) +
           func.coalesce(1.0 / (k + keyword_cte.c.keyword_rank), 0.0)
       )

       final_query = (
           select(
               Chunk,
               rrf_score_expr.label("rrf_score"),
               semantic_cte.c.semantic_rank,
               keyword_cte.c.keyword_rank,
           )
           .select_from(
               semantic_cte.outerjoin(
                   keyword_cte,
                   semantic_cte.c.id == keyword_cte.c.id,
                   full=True
               )
           )
           .join(Chunk, func.coalesce(semantic_cte.c.id, keyword_cte.c.id) == Chunk.id)
           .order_by(rrf_score_expr.desc())
           .limit(top_k)
       )

       results = await session.execute(final_query)

       return [
           {
               "chunk_id": r.Chunk.chunk_id,
               "content": r.Chunk.content,
               "document_id": r.Chunk.document_id,
               "rrf_score": float(r.rrf_score),
               "semantic_rank": r.semantic_rank,
               "keyword_rank": r.keyword_rank,
           }
           for r in results
       ]
   ```

3. **测试代码**:
   ```python
   # tests/unit/test_chunk_hybrid_search.py

   import pytest
   from holo.retrieval.chunk_hybrid_search import chunk_hybrid_search


   @pytest.mark.asyncio
   async def test_chunk_hybrid_search(session, sample_chunks):
       """测试 Chunk 级混合搜索"""
       # 准备测试数据
       query = "test query"
       query_embedding = [0.1] * 1536

       # 执行搜索
       results = await chunk_hybrid_search(
           session=session,
           query=query,
           query_embedding=query_embedding,
           search_space_id=1,
           top_k=10,
       )

       # 验证结果
       assert len(results) > 0
       assert all("rrf_score" in r for r in results)
       assert all("chunk_id" in r for r in results)

       # 验证 RRF 分数递减
       scores = [r["rrf_score"] for r in results]
       assert scores == sorted(scores, reverse=True)
   ```

**预期输出**: 测试通过，返回按 RRF 分数排序的 chunks

**耗时**: 1 天

---

**任务 1.2: 创建 Document 级混合搜索**

**文件**: `src/backend/base/holo/retrieval/document_hybrid_search.py`

**实现步骤**: 与 Chunk 级搜索类似，应用于 Document 表

**代码**:
```python
# 与 chunk_hybrid_search.py 相似，但使用 Document 表
# 搜索 documents.content 和 documents.embedding 字段
```

**耗时**: 1 天

---

**任务 1.3: 创建三层 RRF 组合搜索**

**文件**: `src/backend/base/holo/retrieval/combined_rrf_search.py`

**实现步骤**:

1. **创建文件并实现**:
   ```python
   # src/backend/base/holo/retrieval/combined_rrf_search.py

   from typing import List, Optional, Dict, Any
   from collections import defaultdict
   from sqlalchemy.ext.asyncio import AsyncSession
   from langflow.services.database.models.holo.document import Document
   from langflow.services.database.models.holo.chunk import Chunk
   from holo.retrieval.chunk_hybrid_search import chunk_hybrid_search
   from holo.retrieval.document_hybrid_search import document_hybrid_search
   from sqlalchemy import select


   async def combined_rrf_search(
       session: AsyncSession,
       query: str,
       query_embedding: List[float],
       search_space_id: int,
       top_k: int = 20,
       filters: Optional[dict] = None,
   ) -> List[Dict[str, Any]]:
       """三层 RRF 融合检索

       架构:
       - Layer 1: Chunk-level RRF (vector + keyword)
       - Layer 2: Document-level RRF (vector + keyword)
       - Layer 3: Combined RRF (chunks + documents)

       Args:
           session: 数据库会话
           query: 查询文本
           query_embedding: 查询向量
           search_space_id: 空间 ID
           top_k: 最终返回结果数量
           filters: 额外过滤条件

       Returns:
           最终融合后的文档列表，包含相关 chunks
       """
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
               "rank_in_chunks": idx + 1,  # 排名从 1 开始
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
           if document:
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
           doc_id = doc_result["document_id"]
           if doc_id in all_docs:
               # 更新已有文档
               all_docs[doc_id]["score_from_docs"] = doc_result["rrf_score"]
               all_docs[doc_id]["rank_from_docs"] = idx + 1
           else:
               # 新文档，获取其所有 chunks
               document = await session.get(Document, doc_id)
               if document:
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

2. **创建测试**:
   ```python
   # tests/unit/test_combined_rrf_search.py

   import pytest
   from holo.retrieval.combined_rrf_search import combined_rrf_search


   @pytest.mark.asyncio
   async def test_combined_rrf_search(session, sample_documents_and_chunks):
       """测试三层 RRF 融合搜索"""
       query = "test query"
       query_embedding = [0.1] * 1536

       results = await combined_rrf_search(
           session=session,
           query=query,
           query_embedding=query_embedding,
           search_space_id=1,
           top_k=10,
       )

       # 验证结果
       assert len(results) > 0
       assert all("final_rrf_score" in r for r in results)
       assert all("document" in r for r in results)
       assert all("chunks" in r for r in results)

       # 验证最终分数递减
       scores = [r["final_rrf_score"] for r in results]
       assert scores == sorted(scores, reverse=True)

       # 验证每个文档都有 chunks
       assert all(len(r["chunks"]) > 0 for r in results)
   ```

**耗时**: 2 天

---

#### P0.1 验收标准

- [ ] Chunk 级混合搜索实现并测试通过
- [ ] Document 级混合搜索实现并测试通过
- [ ] 三层 RRF 组合搜索实现并测试通过
- [ ] 性能测试: 1000 chunks 检索 < 500ms
- [ ] 质量测试: NDCG@10 > 0.75（使用测试数据集）
- [ ] 所有单元测试通过

**完成标志**: 运行 `pytest tests/unit/test_combined_rrf_search.py -v` 全部通过

---

### P0.2: RBAC 权限系统（第 3 周）

#### 功能描述

实现完整的基于角色的访问控制（Role-Based Access Control）系统

**包含**:
- 4 个数据库表（Role, SpaceMembership, SpaceInvite, Permission）
- 17 种权限类型
- 4 个预定义系统角色（Owner, Admin, Editor, Viewer）
- 权限检查中间件
- 前端成员和角色管理界面

#### 详细任务

**任务 2.1: 创建 RBAC 数据库模型**

**文件位置**:
- `src/backend/base/langflow/services/database/models/holo/role.py`
- `src/backend/base/langflow/services/database/models/holo/space_membership.py`
- `src/backend/base/langflow/services/database/models/holo/space_invite.py`
- `src/backend/base/langflow/services/database/models/holo/permission.py`

**实现步骤**:

1. **创建权限枚举** (`permission.py`):
   ```python
   # src/backend/base/langflow/services/database/models/holo/permission.py

   from enum import Enum


   class Permission(str, Enum):
       """权限枚举（17 种权限）"""

       # 文档权限
       DOCUMENTS_CREATE = "documents:create"
       DOCUMENTS_READ = "documents:read"
       DOCUMENTS_UPDATE = "documents:update"
       DOCUMENTS_DELETE = "documents:delete"

       # 聊天权限
       CHATS_CREATE = "chats:create"
       CHATS_READ = "chats:read"
       CHATS_UPDATE = "chats:update"
       CHATS_DELETE = "chats:delete"

       # LLM 配置权限
       LLM_CONFIGS_CREATE = "llm_configs:create"
       LLM_CONFIGS_READ = "llm_configs:read"
       LLM_CONFIGS_UPDATE = "llm_configs:update"
       LLM_CONFIGS_DELETE = "llm_configs:delete"

       # 播客权限
       PODCASTS_CREATE = "podcasts:create"
       PODCASTS_READ = "podcasts:read"
       PODCASTS_UPDATE = "podcasts:update"
       PODCASTS_DELETE = "podcasts:delete"

       # 连接器权限
       CONNECTORS_CREATE = "connectors:create"
       CONNECTORS_READ = "connectors:read"
       CONNECTORS_UPDATE = "connectors:update"
       CONNECTORS_DELETE = "connectors:delete"

       # 日志权限
       LOGS_READ = "logs:read"
       LOGS_DELETE = "logs:delete"

       # 成员管理权限
       MEMBERS_INVITE = "members:invite"
       MEMBERS_VIEW = "members:view"
       MEMBERS_REMOVE = "members:remove"
       MEMBERS_MANAGE_ROLES = "members:manage_roles"

       # 角色管理权限
       ROLES_CREATE = "roles:create"
       ROLES_READ = "roles:read"
       ROLES_UPDATE = "roles:update"
       ROLES_DELETE = "roles:delete"

       # 设置权限
       SETTINGS_VIEW = "settings:view"
       SETTINGS_UPDATE = "settings:update"
       SETTINGS_DELETE = "settings:delete"  # 删除空间

       # 完全访问
       FULL_ACCESS = "*"
   ```

2. **创建 Role 模型** (参考阶段 0 的迁移脚本)

3. **创建 SpaceMembership 模型**

4. **创建 SpaceInvite 模型**

**耗时**: 1 天

---

**任务 2.2: 实现 RBAC 服务**

**文件**: `src/backend/base/langflow/services/holo/rbac_service.py`

**实现步骤**:

1. **创建 RBAC 服务类**:
   ```python
   # src/backend/base/langflow/services/holo/rbac_service.py

   from typing import List, Dict
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from langflow.services.database.models.holo.role import Role
   from langflow.services.database.models.holo.space_membership import SpaceMembership
   from langflow.services.database.models.holo.permission import Permission


   # 系统角色定义
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


   class RBACService:
       """RBAC 权限管理服务"""

       @staticmethod
       async def initialize_system_roles(session: AsyncSession, search_space_id: int):
           """初始化系统角色（创建空间时调用）

           Args:
               session: 数据库会话
               search_space_id: 空间 ID
           """
           for role_name, role_config in SYSTEM_ROLES.items():
               role = Role(
                   search_space_id=search_space_id,
                   name=role_name,
                   description=role_config["description"],
                   permissions=role_config["permissions"],
                   is_system_role=role_config["is_system_role"],
                   is_default=role_config["is_default"],
               )
               session.add(role)

           await session.commit()

       @staticmethod
       async def check_permission(
           session: AsyncSession,
           user_id: str,
           search_space_id: int,
           required_permission: str,
       ) -> bool:
           """检查用户是否有指定权限

           Args:
               session: 数据库会话
               user_id: 用户 ID
               search_space_id: 空间 ID
               required_permission: 所需权限（如 "documents:create"）

           Returns:
               是否有权限
           """
           # 获取用户成员关系
           membership = await session.execute(
               select(SpaceMembership)
               .where(
                   SpaceMembership.user_id == user_id,
                   SpaceMembership.search_space_id == search_space_id,
               )
           )
           membership = membership.scalar_one_or_none()

           if not membership:
               return False

           # 获取角色权限
           role = await session.get(Role, membership.role_id)
           if not role:
               return False

           # 检查权限
           if "*" in role.permissions:
               return True  # 完全访问

           # 通配符匹配（如 "documents:*" 匹配 "documents:create"）
           for perm in role.permissions:
               if perm.endswith(":*"):
                   resource = perm.split(":")[0]
                   if required_permission.startswith(f"{resource}:"):
                       return True
               elif perm == required_permission:
                   return True

           return False

       @staticmethod
       async def get_default_role_id(session: AsyncSession, search_space_id: int) -> int:
           """获取默认角色 ID（用于邀请）

           Args:
               session: 数据库会话
               search_space_id: 空间 ID

           Returns:
               默认角色 ID
           """
           result = await session.execute(
               select(Role.id)
               .where(
                   Role.search_space_id == search_space_id,
                   Role.is_default == True,
               )
           )
           return result.scalar_one()
   ```

2. **创建测试**:
   ```python
   # tests/unit/test_rbac_service.py

   import pytest
   from langflow.services.holo.rbac_service import RBACService


   @pytest.mark.asyncio
   async def test_initialize_system_roles(session, sample_space):
       """测试系统角色初始化"""
       await RBACService.initialize_system_roles(session, sample_space.id)

       # 验证 4 个角色已创建
       from langflow.services.database.models.holo.role import Role
       from sqlalchemy import select, func

       count = await session.execute(
           select(func.count(Role.id)).where(Role.search_space_id == sample_space.id)
       )
       assert count.scalar() == 4


   @pytest.mark.asyncio
   async def test_check_permission(session, sample_space, sample_user):
       """测试权限检查"""
       # 初始化角色
       await RBACService.initialize_system_roles(session, sample_space.id)

       # 获取 Editor 角色
       from langflow.services.database.models.holo.role import Role
       from sqlalchemy import select

       role = await session.execute(
           select(Role).where(
               Role.search_space_id == sample_space.id,
               Role.name == "Editor",
           )
       )
       role = role.scalar_one()

       # 创建成员关系
       from langflow.services.database.models.holo.space_membership import SpaceMembership
       membership = SpaceMembership(
           user_id=sample_user.id,
           search_space_id=sample_space.id,
           role_id=role.id,
       )
       session.add(membership)
       await session.commit()

       # 测试权限检查
       has_create = await RBACService.check_permission(
           session, sample_user.id, sample_space.id, "documents:create"
       )
       assert has_create is True

       has_delete_space = await RBACService.check_permission(
           session, sample_user.id, sample_space.id, "settings:delete"
       )
       assert has_delete_space is False
   ```

**耗时**: 2 天

---

**任务 2.3: 创建权限检查中间件**

**文件**: `src/backend/base/langflow/api/v1/dependencies/rbac.py`

**实现步骤**:

```python
# src/backend/base/langflow/api/v1/dependencies/rbac.py

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from langflow.services.database.models.user import User
from langflow.api.v1.schemas import get_current_active_user
from langflow.services.deps import get_session
from langflow.services.holo.rbac_service import RBACService


async def check_permission(
    required_permission: str,
    current_user: User = Depends(get_current_active_user),
    search_space_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """权限检查依赖项（FastAPI Dependency）

    用法:
        @router.post("/documents/")
        async def create_document(
            ...,
            _: None = Depends(check_permission("documents:create")),
        ):
            ...

    Args:
        required_permission: 所需权限
        current_user: 当前用户
        search_space_id: 空间 ID
        session: 数据库会话

    Raises:
        HTTPException: 403 如果没有权限
    """
    has_permission = await RBACService.check_permission(
        session=session,
        user_id=str(current_user.id),
        search_space_id=search_space_id,
        required_permission=required_permission,
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Missing required permission: {required_permission}",
        )
```

**耗时**: 1 天

---

**任务 2.4: 创建前端成员和角色管理界面**

**文件位置**:
- `src/frontend/src/pages/HoloPage/MembersTab.tsx`
- `src/frontend/src/pages/HoloPage/RolesTab.tsx`
- `src/frontend/src/pages/HoloPage/components/MemberList.tsx`
- `src/frontend/src/pages/HoloPage/components/InviteMemberDialog.tsx`
- `src/frontend/src/pages/HoloPage/components/RoleList.tsx`
- `src/frontend/src/pages/HoloPage/components/CreateRoleDialog.tsx`
- `src/frontend/src/pages/HoloPage/components/PermissionMatrix.tsx`

**实现步骤**:

1. **创建 MembersTab**:
   ```typescript
   // src/frontend/src/pages/HoloPage/MembersTab.tsx

   import { useState } from 'react';
   import { Button } from '@/components/ui/button';
   import { MemberList } from './components/MemberList';
   import { InviteMemberDialog } from './components/InviteMemberDialog';
   import { UserPlus } from 'lucide-react';


   export function MembersTab({ spaceId }: { spaceId: number }) {
     const [showInviteDialog, setShowInviteDialog] = useState(false);

     return (
       <div className="space-y-6">
         <div className="flex justify-between items-center">
           <h2 className="text-2xl font-bold">成员管理</h2>
           <Button onClick={() => setShowInviteDialog(true)}>
             <UserPlus className="w-4 h-4 mr-2" />
             邀请成员
           </Button>
         </div>

         <MemberList spaceId={spaceId} />

         <InviteMemberDialog
           spaceId={spaceId}
           open={showInviteDialog}
           onClose={() => setShowInviteDialog(false)}
         />
       </div>
     );
   }
   ```

2. **创建 MemberList 组件**:
   ```typescript
   // src/frontend/src/pages/HoloPage/components/MemberList.tsx

   import { useQuery } from '@tanstack/react-query';
   import { holoAPI } from '@/controllers/API/holo';
   import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
   import { Badge } from '@/components/ui/badge';
   import { Button } from '@/components/ui/button';
   import { Trash2 } from 'lucide-react';


   export function MemberList({ spaceId }: { spaceId: number }) {
     const { data: members, isLoading } = useQuery({
       queryKey: ['space-members', spaceId],
       queryFn: () => holoAPI.listMembers(spaceId),
     });

     if (isLoading) {
       return <div>加载中...</div>;
     }

     return (
       <Table>
         <TableHeader>
           <TableRow>
             <TableHead>用户</TableHead>
             <TableHead>角色</TableHead>
             <TableHead>加入时间</TableHead>
             <TableHead>操作</TableHead>
           </TableRow>
         </TableHeader>
         <TableBody>
           {members?.map((member) => (
             <TableRow key={member.id}>
               <TableCell>{member.user_email}</TableCell>
               <TableCell>
                 {member.is_owner ? (
                   <Badge variant="default">所有者</Badge>
                 ) : (
                   <Badge variant="secondary">{member.role_name}</Badge>
                 )}
               </TableCell>
               <TableCell>
                 {new Date(member.joined_at).toLocaleDateString('zh-CN')}
               </TableCell>
               <TableCell>
                 {!member.is_owner && (
                   <Button variant="ghost" size="sm">
                     <Trash2 className="w-4 h-4" />
                   </Button>
                 )}
               </TableCell>
             </TableRow>
           ))}
         </TableBody>
       </Table>
     );
   }
   ```

3. **创建 InviteMemberDialog**（邀请链接生成器）

4. **创建 RolesTab**（角色管理）

5. **创建 PermissionMatrix**（权限选择器）

**耗时**: 2 天

---

#### P0.2 验收标准

- [ ] 4 个 RBAC 数据库模型已创建
- [ ] RBACService 实现并测试通过
- [ ] 权限检查中间件实现
- [ ] 创建空间时自动初始化 4 个系统角色
- [ ] 前端成员管理界面功能完整
- [ ] 前端角色管理界面功能完整
- [ ] 邀请系统可生成邀请链接
- [ ] 权限检查在 API 端点正常工作

**完成标志**: 创建一个测试空间，邀请一个用户为 Viewer 角色，验证该用户无法创建文档（403 错误）

---

### P0.3: 文档去重系统（第 3 周后半）

#### 功能描述

实现双哈希机制，避免重复索引相同文档：
- **内容哈希**: 检测内容变化
- **唯一标识哈希**: 检测文档身份

**逻辑**:
1. 计算两个哈希值
2. 查询数据库是否存在 unique_identifier_hash
3. 如果存在且 content_hash 相同 → 跳过
4. 如果存在但 content_hash 不同 → 更新（删除旧 chunks，重新索引）
5. 如果不存在 → 创建新文档

#### 详细任务

**任务 3.1: 实现哈希工具函数**

**文件**: `src/backend/base/holo/utils/hash_utils.py`

**实现步骤**:

```python
# src/backend/base/holo/utils/hash_utils.py

import hashlib


def generate_content_hash(content: str, search_space_id: int) -> str:
    """生成内容哈希（检测内容变化）

    Args:
        content: 文档内容
        search_space_id: 空间 ID（多租户隔离）

    Returns:
        SHA256 哈希值（64 字符）
    """
    combined = f"{search_space_id}:{content}"
    return hashlib.sha256(combined.encode()).hexdigest()


def generate_unique_identifier_hash(
    document_type: str,
    unique_identifier: str,
    search_space_id: int,
) -> str:
    """生成唯一标识哈希（检测文档身份）

    Args:
        document_type: 文档类型（如 "GITHUB", "SLACK"）
        unique_identifier: 唯一标识符（如 GitHub URL）
        search_space_id: 空间 ID

    Returns:
        SHA256 哈希值（64 字符）
    """
    combined = f"{search_space_id}:{document_type}:{unique_identifier}"
    return hashlib.sha256(combined.encode()).hexdigest()
```

**测试**:
```python
# tests/unit/test_hash_utils.py

from holo.utils.hash_utils import generate_content_hash, generate_unique_identifier_hash


def test_generate_content_hash():
    """测试内容哈希生成"""
    hash1 = generate_content_hash("test content", 1)
    hash2 = generate_content_hash("test content", 1)
    hash3 = generate_content_hash("different content", 1)

    # 相同内容应产生相同哈希
    assert hash1 == hash2

    # 不同内容应产生不同哈希
    assert hash1 != hash3

    # 哈希长度应为 64
    assert len(hash1) == 64


def test_generate_unique_identifier_hash():
    """测试唯一标识哈希生成"""
    hash1 = generate_unique_identifier_hash("GITHUB", "https://github.com/repo", 1)
    hash2 = generate_unique_identifier_hash("GITHUB", "https://github.com/repo", 1)
    hash3 = generate_unique_identifier_hash("GITHUB", "https://github.com/other", 1)

    # 相同标识符应产生相同哈希
    assert hash1 == hash2

    # 不同标识符应产生不同哈希
    assert hash1 != hash3

    # 多租户隔离：不同空间应产生不同哈希
    hash4 = generate_unique_identifier_hash("GITHUB", "https://github.com/repo", 2)
    assert hash1 != hash4
```

**耗时**: 半天

---

**任务 3.2: 实现增量更新逻辑**

**文件**: `src/backend/base/holo/etl/service.py`

**实现步骤**:

```python
# src/backend/base/holo/etl/service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, UTC
from langflow.services.database.models.holo.document import Document, DocumentType
from langflow.services.database.models.holo.chunk import Chunk
from holo.utils.hash_utils import generate_content_hash, generate_unique_identifier_hash
import logging

logger = logging.getLogger(__name__)


async def process_document(
    content: str,
    document_type: DocumentType,
    unique_identifier: str,
    search_space_id: int,
    session: AsyncSession,
    metadata: dict = None,
    title: str = None,
    source_url: str = None,
) -> Document:
    """处理文档（支持增量更新和去重）

    逻辑:
    1. 计算内容哈希和唯一标识哈希
    2. 查询是否存在相同的 unique_identifier_hash
    3. 如果存在且内容哈希相同 → 跳过
    4. 如果存在但内容哈希不同 → 更新（重新索引）
    5. 如果不存在 → 创建新文档

    Args:
        content: 文档内容（Markdown 格式）
        document_type: 文档类型
        unique_identifier: 唯一标识符（如 GitHub URL）
        search_space_id: 空间 ID
        session: 数据库会话
        metadata: 文档元数据
        title: 文档标题
        source_url: 源 URL

    Returns:
        Document 对象（新建或更新后的）
    """
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
            # 内容未变，跳过
            logger.info(f"Document {unique_identifier} unchanged, skipping")
            return existing

        # 4. 内容变化，更新
        logger.info(f"Document {unique_identifier} changed, updating")

        # 4.1 删除旧 chunks
        await session.execute(delete(Chunk).where(Chunk.document_id == existing.id))

        # 4.2 生成新内容（摘要 + embedding + chunks）
        # 注意：这里需要调用 ETL 服务生成摘要、embedding 和 chunks
        # 为了示例，这里简化处理
        summary = content[:500]  # 简化：前 500 字符作为摘要
        embedding = [0.1] * 1536  # 简化：需要实际调用 embedding 服务

        # 生成 chunks（需要实际调用 chunker）
        # chunks = await create_document_chunks(content, chunker, embedding_model)

        # 4.3 更新
        existing.content = summary
        existing.embedding = embedding
        existing.content_hash = content_hash
        existing.document_metadata = metadata or {}
        existing.updated_at = datetime.now(UTC)

        # 添加新 chunks
        # for chunk in chunks:
        #     chunk.document_id = existing.id
        #     session.add(chunk)

        await session.commit()
        return existing

    else:
        # 5. 新文档，创建
        logger.info(f"Document {unique_identifier} is new, creating")

        # 生成摘要、embedding 和 chunks（简化）
        summary = content[:500]
        embedding = [0.1] * 1536
        # chunks = await create_document_chunks(content, chunker, embedding_model)

        document = Document(
            search_space_id=search_space_id,
            document_type=document_type,
            document_id=unique_identifier,
            title=title,
            source_url=source_url,
            content=summary,
            embedding=embedding,
            content_hash=content_hash,
            unique_identifier_hash=unique_hash,
            document_metadata=metadata or {},
            # chunks=chunks,  # SQLAlchemy 关系
        )

        session.add(document)
        await session.commit()
        return document
```

**测试**:
```python
# tests/unit/test_document_dedup.py

import pytest
from holo.etl.service import process_document
from langflow.services.database.models.holo.document import DocumentType


@pytest.mark.asyncio
async def test_document_dedup_new_document(session):
    """测试新文档创建"""
    doc = await process_document(
        content="test content",
        document_type=DocumentType.GITHUB,
        unique_identifier="https://github.com/test/repo",
        search_space_id=1,
        session=session,
        title="Test Document",
    )

    assert doc.id is not None
    assert doc.content_hash is not None
    assert doc.unique_identifier_hash is not None


@pytest.mark.asyncio
async def test_document_dedup_unchanged(session):
    """测试内容未变化时跳过"""
    # 第一次创建
    doc1 = await process_document(
        content="test content",
        document_type=DocumentType.GITHUB,
        unique_identifier="https://github.com/test/repo",
        search_space_id=1,
        session=session,
    )

    # 第二次处理（内容相同）
    doc2 = await process_document(
        content="test content",
        document_type=DocumentType.GITHUB,
        unique_identifier="https://github.com/test/repo",
        search_space_id=1,
        session=session,
    )

    # 应该返回相同的文档（ID 相同）
    assert doc1.id == doc2.id


@pytest.mark.asyncio
async def test_document_dedup_content_changed(session):
    """测试内容变化时更新"""
    # 第一次创建
    doc1 = await process_document(
        content="original content",
        document_type=DocumentType.GITHUB,
        unique_identifier="https://github.com/test/repo",
        search_space_id=1,
        session=session,
    )
    original_content_hash = doc1.content_hash

    # 第二次处理（内容变化）
    doc2 = await process_document(
        content="updated content",
        document_type=DocumentType.GITHUB,
        unique_identifier="https://github.com/test/repo",
        search_space_id=1,
        session=session,
    )

    # 应该返回相同的文档（ID 相同），但内容哈希不同
    assert doc1.id == doc2.id
    assert doc2.content_hash != original_content_hash
```

**耗时**: 1.5 天

---

#### P0.3 验收标准

- [ ] 哈希工具函数实现并测试通过
- [ ] 增量更新逻辑实现
- [ ] 新文档正确创建
- [ ] 内容未变化时正确跳过
- [ ] 内容变化时正确更新（删除旧 chunks，重新索引）
- [ ] 多租户隔离正确（不同空间的相同文档产生不同哈希）

**完成标志**: 运行 `pytest tests/unit/test_document_dedup.py -v` 全部通过

---

### P0.4: BlockNote 实时编辑 + 后台重索引（第 4 周）

#### 功能描述

实现实时文档编辑功能：
- 前端使用 BlockNote 富文本编辑器
- 自动保存（1 秒防抖）
- 保存时标记 `content_needs_reindexing = true`
- 后台定期检查并重新索引需要更新的文档

#### 详细任务

**任务 4.1: 扩展 Document 模型**

已在阶段 0 的迁移中完成，包含字段：
- `blocknote_document` (JSONB) - BlockNote 编辑器状态
- `content_needs_reindexing` (Boolean) - 重索引标记

**耗时**: 已完成

---

**任务 4.2: 创建前端 BlockNote 编辑器组件**

**文件**: `src/frontend/src/components/holoComponents/BlockNoteEditor.tsx`

**实现步骤**:

```typescript
// src/frontend/src/components/holoComponents/BlockNoteEditor.tsx

import { useEffect } from 'react';
import { BlockNoteEditor, BlockNoteView, useCreateBlockNote } from '@blocknote/react';
import '@blocknote/core/fonts/inter.css';
import '@blocknote/react/style.css';
import { useMutation } from '@tanstack/react-query';
import { holoAPI } from '@/controllers/API/holo';
import { useDebouncedCallback } from 'use-debounce';


interface BlockNoteEditorProps {
  documentId: number;
  initialContent?: string;  // JSON 字符串
  onSave?: () => void;
}


export function BlockNoteEditorComponent({
  documentId,
  initialContent,
  onSave,
}: BlockNoteEditorProps) {
  // 创建 BlockNote 编辑器实例
  const editor = useCreateBlockNote({
    initialContent: initialContent ? JSON.parse(initialContent) : undefined,
  });

  // 保存 mutation
  const { mutate: saveDocument } = useMutation({
    mutationFn: (content: string) =>
      holoAPI.updateDocument(documentId, {
        blocknote_document: content,
        content_needs_reindexing: true,
      }),
    onSuccess: () => {
      onSave?.();
    },
  });

  // 自动保存（1 秒防抖）
  const debouncedSave = useDebouncedCallback(async () => {
    const content = JSON.stringify(editor.document);
    saveDocument(content);
  }, 1000);

  // 监听编辑器变化
  useEffect(() => {
    const unsubscribe = editor.onChange(() => {
      debouncedSave();
    });

    return () => {
      unsubscribe();
    };
  }, [editor, debouncedSave]);

  return (
    <div className="border rounded-lg p-4">
      <BlockNoteView
        editor={editor}
        theme="light"
      />
    </div>
  );
}
```

**耗时**: 1 天

---

**任务 4.3: 创建 BlockNote → Markdown 转换工具**

**文件**: `src/backend/base/holo/utils/blocknote_utils.py`

**实现步骤**:

```python
# src/backend/base/holo/utils/blocknote_utils.py

from typing import Dict, List


def blocknote_to_markdown(blocknote_json: dict) -> str:
    """将 BlockNote JSON 转换为 Markdown

    BlockNote 格式示例:
    {
        "blocks": [
            {
                "type": "heading",
                "props": {"level": 1},
                "content": [{"type": "text", "text": "Title"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Content"}]
            }
        ]
    }

    Args:
        blocknote_json: BlockNote 编辑器的 JSON 状态

    Returns:
        Markdown 文本
    """
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
        elif block_type == "checkListItem":
            checked = block.get("props", {}).get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            markdown_lines.append(f"- {checkbox} {text}")
        # 可以添加更多块类型支持

        markdown_lines.append("")  # 空行分隔

    return "\n".join(markdown_lines)
```

**测试**:
```python
# tests/unit/test_blocknote_utils.py

from holo.utils.blocknote_utils import blocknote_to_markdown


def test_blocknote_to_markdown_heading():
    """测试标题转换"""
    blocknote_json = {
        "blocks": [
            {
                "type": "heading",
                "props": {"level": 1},
                "content": [{"type": "text", "text": "Title"}]
            }
        ]
    }

    markdown = blocknote_to_markdown(blocknote_json)
    assert "# Title" in markdown


def test_blocknote_to_markdown_paragraph():
    """测试段落转换"""
    blocknote_json = {
        "blocks": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "This is a paragraph"}]
            }
        ]
    }

    markdown = blocknote_to_markdown(blocknote_json)
    assert "This is a paragraph" in markdown


def test_blocknote_to_markdown_list():
    """测试列表转换"""
    blocknote_json = {
        "blocks": [
            {
                "type": "bulletListItem",
                "content": [{"type": "text", "text": "Item 1"}]
            },
            {
                "type": "bulletListItem",
                "content": [{"type": "text", "text": "Item 2"}]
            }
        ]
    }

    markdown = blocknote_to_markdown(blocknote_json)
    assert "- Item 1" in markdown
    assert "- Item 2" in markdown
```

**耗时**: 1 天

---

**任务 4.4: 创建后台重索引任务**

**文件**: `src/backend/base/langflow/tasks/etl_tasks.py`

**实现步骤**:

```python
# src/backend/base/langflow/tasks/etl_tasks.py

from celery import shared_task
from sqlalchemy import select, delete
from langflow.services.database.models.holo.document import Document
from langflow.services.database.models.holo.chunk import Chunk
from holo.utils.blocknote_utils import blocknote_to_markdown
from langflow.services.deps import get_session
import logging

logger = logging.getLogger(__name__)


@shared_task(name="reindex_blocknote_document")
async def reindex_blocknote_document(document_id: int):
    """BlockNote 文档后台重索引

    步骤:
    1. 转换 BlockNote JSON → Markdown
    2. 重新生成摘要 + Embedding
    3. 重新分块 + Embedding
    4. 更新数据库

    Args:
        document_id: 文档 ID
    """
    async with get_session() as session:
        document = await session.get(Document, document_id)

        if not document or not document.blocknote_document:
            logger.warning(f"Document {document_id} not found or has no blocknote content")
            return

        try:
            # 1. 转换 BlockNote JSON → Markdown
            markdown = blocknote_to_markdown(document.blocknote_document)

            # 2. 重新生成摘要 + Embedding
            # 注意：这里需要调用实际的 LLM 和 Embedding 服务
            # 为了示例，这里简化处理
            summary = markdown[:500]  # 简化：前 500 字符
            embedding = [0.1] * 1536  # 简化：需要实际调用 embedding 服务

            # 3. 重新分块 + Embedding
            # 删除旧 chunks
            await session.execute(
                delete(Chunk).where(Chunk.document_id == document_id)
            )

            # 生成新 chunks（需要实际调用 chunker）
            # chunks = await create_document_chunks(markdown, chunker, embedding_model)

            # 4. 更新文档
            document.content = summary
            document.embedding = embedding
            document.content_needs_reindexing = False

            # 添加新 chunks
            # for chunk in chunks:
            #     chunk.document_id = document_id
            #     session.add(chunk)

            await session.commit()

            logger.info(f"Reindexed document {document_id} successfully")

        except Exception as e:
            logger.error(f"Failed to reindex document {document_id}: {e}")
            raise


@shared_task(name="check_documents_needing_reindexing")
async def check_documents_needing_reindexing():
    """检查需要重索引的文档（定期任务）

    扫描所有 content_needs_reindexing = true 的文档，
    触发重索引任务
    """
    async with get_session() as session:
        docs = await session.execute(
            select(Document.id).where(Document.content_needs_reindexing == True)
        )

        count = 0
        for doc_id in docs.scalars():
            reindex_blocknote_document.delay(doc_id)
            count += 1

        logger.info(f"Scheduled {count} documents for reindexing")
```

**配置 Celery Beat**:
```python
# src/backend/base/langflow/celery_app.py

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # ... 其他定期任务 ...

    "check-documents-needing-reindexing": {
        "task": "check_documents_needing_reindexing",
        "schedule": crontab(minute="*/10"),  # 每 10 分钟检查一次
    },
}
```

**耗时**: 1 天

---

#### P0.4 验收标准

- [ ] BlockNote 编辑器组件实现
- [ ] 自动保存功能正常（1 秒防抖）
- [ ] 保存时正确标记 `content_needs_reindexing = true`
- [ ] BlockNote → Markdown 转换正确
- [ ] 后台重索引任务实现
- [ ] Celery Beat 定期检查任务配置
- [ ] 重索引后文档内容和 chunks 正确更新
- [ ] 前端编辑器流畅无卡顿

**完成标志**: 在前端编辑一个文档，等待 10 分钟，验证文档的 chunks 已更新为新内容

---

### P0.5: Meta-scheduler 定期索引调度（第 5 周）

#### 功能描述

实现元调度器（Meta-scheduler），支持连接器的定期自动索引：
- 连接器可配置索引频率（15 分钟、30 分钟、1 小时、每天）
- 元调度器定期检查到期的连接器
- 自动触发索引任务

**架构**:
```
Celery Beat (可配置间隔) → check_periodic_schedules 任务
    ↓
检查 next_scheduled_at <= 现在 的连接器
    ↓
更新 next_scheduled_at
    ↓
触发对应的索引任务 (index_github_connector, index_slack_connector, etc.)
```

#### 详细任务

**任务 5.1: 扩展 Connector 模型**

已在阶段 0 的迁移中完成，包含字段：
- `periodic_indexing_enabled` (Boolean)
- `indexing_frequency_minutes` (Integer)
- `next_scheduled_at` (DateTime)

**耗时**: 已完成

---

**任务 5.2: 创建调度检查器任务**

**文件**: `src/backend/base/langflow/tasks/schedule_checker_task.py`

**实现步骤**:

```python
# src/backend/base/langflow/tasks/schedule_checker_task.py

from celery import shared_task
from sqlalchemy import select
from datetime import datetime, timedelta, UTC
from langflow.services.database.models.holo.connector import Connector
from langflow.services.deps import get_session
from langflow.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@shared_task(name="check_periodic_schedules")
async def check_periodic_schedules():
    """检查并触发到期的定期索引任务

    逻辑:
    1. 查找 periodic_indexing_enabled = true 且 next_scheduled_at <= 现在 的连接器
    2. 更新 next_scheduled_at = 现在 + indexing_frequency_minutes
    3. 触发对应的索引任务
    """
    async with get_session() as session:
        now = datetime.now(UTC)

        # 查找到期的连接器
        connectors = await session.execute(
            select(Connector).where(
                Connector.periodic_indexing_enabled == True,
                Connector.next_scheduled_at <= now,
            )
        )

        triggered_count = 0
        for connector in connectors.scalars():
            try:
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

                triggered_count += 1

                logger.info(
                    f"Scheduled indexing for connector {connector.id} "
                    f"(type={connector.connector_type}, "
                    f"next_run={connector.next_scheduled_at})"
                )

            except Exception as e:
                logger.error(f"Failed to schedule connector {connector.id}: {e}")
                # 继续处理其他连接器

        logger.info(f"Triggered {triggered_count} periodic indexing tasks")
```

**耗时**: 1 天

---

**任务 5.3: 配置 Celery Beat 动态间隔**

**文件**: `src/backend/base/langflow/celery_app.py`

**实现步骤**:

```python
# src/backend/base/langflow/celery_app.py

from celery.schedules import crontab
import os


# 环境变量配置调度间隔
SCHEDULE_CHECKER_INTERVAL = os.getenv("SCHEDULE_CHECKER_INTERVAL", "5m")  # 默认 5 分钟


def parse_interval(interval_str: str) -> dict:
    """解析间隔字符串为 crontab 参数

    支持格式:
    - "1m", "5m", "10m" → 每 N 分钟
    - "1h", "2h" → 每 N 小时

    Args:
        interval_str: 间隔字符串

    Returns:
        crontab 参数字典
    """
    if interval_str.endswith("m"):
        minutes = int(interval_str[:-1])
        return {"minute": f"*/{minutes}"}
    elif interval_str.endswith("h"):
        hours = int(interval_str[:-1])
        return {"hour": f"*/{hours}", "minute": "0"}
    else:
        # 默认 5 分钟
        return {"minute": "*/5"}


# 配置 Celery Beat 定期任务
celery_app.conf.beat_schedule = {
    # ... 其他定期任务 ...

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

**耗时**: 半天

---

**任务 5.4: 创建连接器配置界面**

**文件**: `src/frontend/src/pages/HoloPage/components/ConnectorConfigDialog.tsx`

**实现步骤**:

```typescript
// src/frontend/src/pages/HoloPage/components/ConnectorConfigDialog.tsx

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { holoAPI } from '@/controllers/API/holo';


interface ConnectorConfigDialogProps {
  connector: any;
  open: boolean;
  onClose: () => void;
}


export function ConnectorConfigDialog({
  connector,
  open,
  onClose,
}: ConnectorConfigDialogProps) {
  const queryClient = useQueryClient();

  const [periodicEnabled, setPeriodicEnabled] = useState(
    connector.periodic_indexing_enabled || false
  );
  const [frequency, setFrequency] = useState(
    connector.indexing_frequency_minutes || 60
  );

  const { mutate: updateConnector } = useMutation({
    mutationFn: () =>
      holoAPI.updateConnector(connector.id, {
        periodic_indexing_enabled: periodicEnabled,
        indexing_frequency_minutes: frequency,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      onClose();
    },
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>定期索引配置</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* 启用开关 */}
          <div className="flex items-center justify-between">
            <Label htmlFor="periodic-enabled">启用定期索引</Label>
            <Switch
              id="periodic-enabled"
              checked={periodicEnabled}
              onCheckedChange={setPeriodicEnabled}
            />
          </div>

          {/* 频率选择 */}
          {periodicEnabled && (
            <div className="space-y-2">
              <Label>索引频率</Label>
              <Select
                value={frequency.toString()}
                onValueChange={(value) => setFrequency(parseInt(value))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">每 15 分钟</SelectItem>
                  <SelectItem value="30">每 30 分钟</SelectItem>
                  <SelectItem value="60">每小时</SelectItem>
                  <SelectItem value="1440">每天</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* 保存按钮 */}
          <Button onClick={() => updateConnector()} className="w-full">
            保存配置
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**耗时**: 1 天

---

**任务 5.5: 测试定期调度**

**文件**: `tests/unit/test_schedule_checker.py`

**实现步骤**:

```python
# tests/unit/test_schedule_checker.py

import pytest
from datetime import datetime, timedelta, UTC
from langflow.tasks.schedule_checker_task import check_periodic_schedules
from langflow.services.database.models.holo.connector import Connector, ConnectorType


@pytest.mark.asyncio
async def test_schedule_checker_triggers_due_connectors(session, sample_space):
    """测试调度检查器触发到期的连接器"""
    # 创建一个到期的连接器
    connector = Connector(
        space_id=sample_space.id,
        user_id=sample_space.user_id,
        name="Test Connector",
        connector_type=ConnectorType.GITHUB,
        periodic_indexing_enabled=True,
        indexing_frequency_minutes=60,
        next_scheduled_at=datetime.now(UTC) - timedelta(minutes=5),  # 5 分钟前到期
    )
    session.add(connector)
    await session.commit()

    # 运行调度检查器
    await check_periodic_schedules()

    # 验证 next_scheduled_at 已更新
    await session.refresh(connector)
    assert connector.next_scheduled_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_schedule_checker_skips_not_due_connectors(session, sample_space):
    """测试调度检查器跳过未到期的连接器"""
    # 创建一个未到期的连接器
    connector = Connector(
        space_id=sample_space.id,
        user_id=sample_space.user_id,
        name="Test Connector",
        connector_type=ConnectorType.GITHUB,
        periodic_indexing_enabled=True,
        indexing_frequency_minutes=60,
        next_scheduled_at=datetime.now(UTC) + timedelta(minutes=30),  # 30 分钟后到期
    )
    session.add(connector)
    await session.commit()

    original_next_run = connector.next_scheduled_at

    # 运行调度检查器
    await check_periodic_schedules()

    # 验证 next_scheduled_at 未变化
    await session.refresh(connector)
    assert connector.next_scheduled_at == original_next_run
```

**耗时**: 1 天

---

#### P0.5 验收标准

- [ ] 调度检查器任务实现
- [ ] Celery Beat 配置正确（可通过环境变量调整间隔）
- [ ] 到期的连接器正确触发索引任务
- [ ] 未到期的连接器不触发
- [ ] `next_scheduled_at` 正确更新
- [ ] 前端配置界面功能完整
- [ ] 用户可启用/禁用定期索引
- [ ] 用户可选择索引频率（15 分钟、30 分钟、1 小时、每天）

**完成标志**: 创建一个连接器，设置定期索引频率为 15 分钟，等待 15 分钟，验证索引任务被自动触发

---

## 阶段 1 总验收标准

### 功能验收

- [ ] **P0.1 三层 RRF** - 检索质量满足要求（NDCG@10 > 0.75）
- [ ] **P0.2 RBAC** - 权限系统完整功能正常
- [ ] **P0.3 去重** - 文档去重逻辑正确
- [ ] **P0.4 BlockNote** - 实时编辑和后台重索引正常
- [ ] **P0.5 Meta-scheduler** - 定期索引自动执行

### 性能验收

- [ ] 三层 RRF 检索 1000 chunks < 500ms
- [ ] 权限检查 < 50ms
- [ ] BlockNote 编辑流畅无卡顿

### 代码质量

- [ ] 所有单元测试通过
- [ ] 代码格式化（`make format_backend`）
- [ ] 代码检查（`make lint`）
- [ ] 英文注释和文档字符串

**完成标志**: 运行 `pytest src/backend/tests/unit/ -v` 所有 P0 功能测试通过

---

## 后续阶段概述

### 阶段 2: P1 功能（第 6-9 周）

**目标**: 实现关键质量提升功能

**包含功能**:
- P1.1 Reranker 服务（第 6 周）
- P1.2 全局 LLM 配置（第 6 周）
- P1.3 LiteLLM 统一接口（第 7 周）
- P1.4 引用系统（第 8 周）
- P1.5 日志系统（第 9 周）

### 阶段 3: P2 功能（第 10-13 周）

**目标**: 实现重要增强功能

**包含功能**:
- P2.1 Podcaster Agent（第 10 周）
- P2.2 DeepAgents 集成（第 11 周）
- P2.3 LangGraph Checkpointer（第 11 周）
- P2.4 页面配额系统（第 12 周）
- P2.5 Web 搜索连接器（第 13 周）

### 阶段 4: P3 功能（第 14-16 周）

**目标**: 实现性能优化功能

**包含功能**:
- P3.1 多 ETL 服务切换（第 14 周）
- P3.2 Chonkie 智能分块（第 14 周）
- P3.3 Docling GPU 支持（第 15 周）
- P3.4 YouTube 转录（第 15 周）
- P3.5 S3 存储支持（第 16 周）

---

## ⚠️ 关键注意事项

### 1. 不要低估 SurfSense 复杂度

SurfSense 是一个企业级 RAG 系统：
- 124 个 Python 文件（54,000+ 行代码）
- 262 个 TypeScript 文件
- 20+ 个主要功能模块

### 2. 必须实现 P0 功能

P0 功能是系统运行的基础，缺少任何一个都会导致系统无法正常工作。

### 3. 使用 pgvector，不是 Milvus

SurfSense 实际使用的是 PostgreSQL 的 pgvector 扩展，不是 Milvus。这简化了架构。

### 4. 严格遵循 SurfSense 实现模式

SurfSense 的实现已经过验证，不要重新发明轮子：
- 三层 RRF 算法 → 使用精确实现
- RBAC 权限系统 → 使用精确的 17 种权限
- BlockNote 集成 → 使用精确的自动保存模式
- Meta-scheduler → 使用精确的 Celery Beat 模式

---

## ✅ 项目成功标准

### 技术成功

- [ ] 所有 P0 功能实现并测试
- [ ] 三层 RRF 达到 NDCG@10 > 0.75
- [ ] RBAC 权限系统功能完整
- [ ] 实时编辑流畅工作
- [ ] 定期索引按计划执行
- [ ] 无关键 Bug

### 架构成功

- [ ] 使用自然命名（无不必要的 "holo_" 前缀）
- [ ] 代码在 Langflow 现有目录
- [ ] 所有依赖在主依赖列表
- [ ] 国际化完成（仅英文注释）
- [ ] 对齐 SurfSense 代码库模式

### 质量成功

- [ ] 代码质量通过 `make format_backend` 和 `make lint`
- [ ] 所有组件有单元测试
- [ ] 性能满足基准（检索 < 500ms，重排序 < 200ms）
- [ ] 文档完整
- [ ] 用户测试成功

---

## 📚 参考文档

### 必读文档

1. **HOLO_INTEGRATION_COMPLETE_FEATURES.md** (109,764 字符)
   - 所有 SurfSense 功能的完整审计
   - 完整代码实现
   - 数据库模型、服务、API 端点、前端组件
   - **开始实施前必读**

2. **NAMING_CONFLICT_MATRIX.md**
   - 证明无冲突的审计
   - 自然命名的合理性（Connector、Space、Document）

3. **HOLO_QUICK_VALIDATION_PLAN.md**
   - 2 周 MVP 验证计划
   - 可用于早期原型

---

## 🎯 下一步行动

1. **审查此计划** - 与团队确认完整性
2. **验证优先级** - 确认 P0-P3 符合预期
3. **开始阶段 0** - 环境设置和迁移
4. **执行阶段 1** - P0 功能实施

---

**文档版本**: v1.0
**创建日期**: 2025-12-29
**作者**: Claude (Sonnet 4.5)
**状态**: 准备执行

**参考文档**:
- `HOLO_INTEGRATION_COMPLETE_FEATURES.md` - 完整功能审计
- `NAMING_CONFLICT_MATRIX.md` - 命名冲突分析
- `HOLO_QUICK_VALIDATION_PLAN.md` - 2 周 MVP 计划
- `HOLO_INTEGRATION_PLAN_REVISED.md` - 英文版完整计划
