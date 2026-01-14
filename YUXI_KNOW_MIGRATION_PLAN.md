# Yuxi-Know 图谱知识库融合到 SurfSense 完整方案

## 执行摘要

本文档描述了将 Yuxi-Know 项目的**图谱知识库能力**（语义查询 + 知识构建）深度融合到 SurfSense 前后端的完整实施方案。

**核心目标**:
- ✅ 图谱能力在前后端 SurfSense 中集成使用
- ✅ 包含语义查询 (LightRAG 混合检索：向量+图谱)
- ✅ 包含知识构建 (实体提取、关系构建、图谱生成)
- ✅ 前端统一到 React (Vue → React 迁移)
- ✅ 真正融合，不是简单的功能叠加

**预计工时**: 540-690 小时 (10.5-13 周，2人团队)

**技术栈**:
- 后端: Python + FastAPI + SQLModel + PostgreSQL + Neo4j (可选)
- 前端: React + TypeScript + Zustand + AntV G6
- 检索: LightRAG (向量 + 图谱混合)
- 异步处理: Celery + Redis

---

## 一、项目背景分析

### 1.1 Yuxi-Know 项目概况

**代码统计**:
- 82 个 Python 文件
- ~14,854 行代码

**需要迁移的核心能力**:
- 图谱知识库系统 (~3,000 行)
- 语义查询接口 (~500 行)
- 知识构建管道 (~1,000 行)
- 图谱可视化前端 (~1,500 行)

**不需迁移**:
- Agent 系统
- LangGraph 工作流
- MCP (Model Context Protocol)

**核心技术**:
```python
# Yuxi-Know 核心实现
/Users/jiangwei/Python/Yuxi-Know/
├── src/knowledge/implementations/lightrag.py    # LightRAG 实现
├── src/knowledge/adapters/lightrag_to_graph.py  # 图谱适配器
├── src/knowledge/indexing.py                    # 实体提取
└── web/src/components/Graph/KnowledgeGraph.vue  # Vue 图谱可视化
```

### 1.2 SurfSense 现状分析

**已完成的基础能力**:

```python
# 现有后端架构
langflow/src/backend/base/langflow/
├── services/database/models/
│   ├── document/model.py          ✅ 文档模型 (支持embedding)
│   ├── chunk/model.py             ✅ 文本块模型 (支持embedding)
│   ├── connector/model.py         ✅ 15个数据源连接器
│   └── space/model.py             ✅ 空间隔离
│
├── api/v1/
│   ├── documents.py               ✅ 文档CRUD + 简单搜索
│   ├── connectors.py              ✅ 连接器管理 + 索引任务
│   └── knowledge_bases.py         ✅ 知识库元数据
│
└── services/
    ├── query/service.py           ✅ 查询重构 (用LLM优化)
    └── docling/                   ✅ 文档解析
```

**关键缺失能力**:

❌ **后端缺失**:
1. Entity/Relation 数据模型 (PostgreSQL 表)
2. 实体/关系提取管道 (Celery 后台任务)
3. 图谱查询 API (`/api/v1/entities`, `/api/v1/graphs`)
4. LightRAG 集成 (语义查询引擎)
5. Neo4j 图谱存储 (可选，可先用 PostgreSQL)

❌ **前端缺失**:
1. 图谱可视化组件 (G6 或 Cytoscape.js)
2. 实体浏览器 (Entity Browser)
3. 统一搜索接口 (文档+实体混合搜索)
4. 图谱Tab (在知识库页面中)

**现有搜索实现的局限性**:

```python
# 当前 documents.py 的搜索实现 (第 359 行)
async def search_documents(
    title: str,
    # ...
):
    # ⚠️ 仅支持标题的模糊匹配，无语义搜索
    query = query.filter(Document.title.ilike(f"%{title}%"))
```

**发现**: 尽管 Document 和 Chunk 模型有 `embedding` 字段，但当前**未实现向量检索**，仅有简单的 SQL ILIKE 匹配。

---

## 二、融合架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│              SurfSense 融合图谱后架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【用户层】                                                   │
│  ├── 上传文档 → 自动触发图谱构建                             │
│  ├── 查询知识 → 混合检索 (文档+实体+关系)                   │
│  └── 浏览图谱 → 交互式图谱可视化                             │
│                                                             │
│  ═════════════════════════════════════════════════════      │
│                                                             │
│  【处理管道】 (融合点 1: 文档索引)                           │
│  ├── 文档上传/连接器导入                                      │
│  ├── ├─→ 解析 (Docling/Unstructured)       ✅ 现有         │
│  ├── ├─→ 分块 (Chonkie)                    ✅ 现有         │
│  ├── ├─→ Embedding (OpenAI/Cohere)         ✅ 现有         │
│  ├── ├─→ [新] 实体提取 (LLM/NER)           ⭐ 新增         │
│  ├── ├─→ [新] 关系提取 (LLM)               ⭐ 新增         │
│  ├── ├─→ [新] 图谱构建 (去重+索引)         ⭐ 新增         │
│  └── └─→ 存储 (PostgreSQL + Neo4j)                        │
│                                                             │
│  【存储层】 (融合点 2: 数据模型)                             │
│  ├── PostgreSQL                                            │
│  │   ├── Document + Chunk                  ✅ 现有         │
│  │   ├── [新] Entity                       ⭐ 新增         │
│  │   └── [新] Relation                     ⭐ 新增         │
│  ├── Vector Store (Chroma/Qdrant)         ✅ 现有         │
│  └── [新] Neo4j (可选,图谱优化)            ⭐ 新增         │
│                                                             │
│  【检索层】 (融合点 3: 统一搜索)                             │
│  ├── 文档检索 (向量 + 全文)                ✅ 现有         │
│  ├── [新] 实体检索 (图谱遍历)              ⭐ 新增         │
│  └── [新] 混合检索 (文档+实体+关系)        ⭐ 新增         │
│                                                             │
│  【API层】 (融合点 4: 统一接口)                              │
│  ├── /documents                            ✅ 现有         │
│  ├── [新] /entities                        ⭐ 新增         │
│  ├── [新] /graphs                          ⭐ 新增         │
│  └── [扩展] /search?mode=hybrid            ⭐ 扩展         │
│                                                             │
│  【前端层】 (融合点 5: UI 融合)                              │
│  ├── 知识库页面                            ✅ 现有         │
│  │   ├── Documents Tab                     ✅ 现有         │
│  │   ├── [新] Graph Tab                    ⭐ 新增         │
│  │   └── [新] Entities Tab                 ⭐ 新增         │
│  └── [新] 统一搜索面板                      ⭐ 新增         │
│      ├── 搜索框 (同时匹配文档+实体)                          │
│      ├── 结果展示 (混合显示)                                 │
│      └── 交叉链接 (文档↔实体)                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 融合原则

**不是两套系统并存，而是深度融合**:

1. **数据融合**: Entity/Relation 与 Document/Chunk 在同一数据库，通过外键关联
2. **流程融合**: 文档上传时自动触发实体提取，无需用户额外操作
3. **检索融合**: 单一搜索接口同时返回文档和实体结果
4. **UI融合**: 在现有知识库页面中添加Tab，而非独立页面
5. **权限融合**: Entity/Relation 继承 Space 的 RBAC 权限

---

## 三、实施方案

### Phase 1: 数据模型融合 (第 1-1.5 周)

#### 1.1 新增数据库表

**迁移文件位置**: `langflow/alembic/versions/xxx_add_knowledge_graph_tables.py`

**Entity 表结构**:

```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class Entity(SQLModel, table=True):
    """实体模型 - 从文档中提取的知识实体"""
    __tablename__ = "entity"

    # 主键和外键
    id: int = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="space.id", index=True)
    document_id: int | None = Field(default=None, foreign_key="document.id")
    chunk_id: int | None = Field(default=None, foreign_key="chunk.id")

    # 实体属性
    name: str = Field(index=True, max_length=500)
    entity_type: str = Field(index=True, max_length=100)  # Person, Organization, Location, Concept等
    description: str | None = Field(default=None, max_length=2000)
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSON))  # 别名

    # 向量嵌入 (用于实体检索)
    embedding: list[float] | None = Field(default=None, sa_column=Column(JSON))

    # 额外属性
    properties: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)

    class Config:
        arbitrary_types_allowed = True
```

**Relation 表结构**:

```python
class Relation(SQLModel, table=True):
    """关系模型 - 实体之间的关系"""
    __tablename__ = "relation"

    # 主键和外键
    id: int = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="space.id", index=True)
    source_entity_id: int = Field(foreign_key="entity.id", index=True)
    target_entity_id: int = Field(foreign_key="entity.id", index=True)
    document_id: int | None = Field(default=None, foreign_key="document.id")
    chunk_id: int | None = Field(default=None, foreign_key="chunk.id")

    # 关系属性
    relation_type: str = Field(index=True, max_length=100)  # PartOf, LeadsTo, RelatedTo等
    description: str | None = Field(default=None, max_length=2000)
    weight: float = Field(default=1.0)  # 关系权重/置信度

    # 额外属性
    properties: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
```

**扩展 Space 表** (添加图谱配置):

```python
# 在现有 Space 模型中添加字段
class Space(SQLModel, table=True):
    # ... 现有字段 ...

    # 新增：图谱配置
    enable_knowledge_graph: bool = Field(default=False)  # 是否启用图谱构建
    graph_llm_config_id: int | None = Field(default=None, foreign_key="llm_config.id")  # 实体提取用的LLM
    auto_entity_extraction: bool = Field(default=True)  # 是否自动提取实体
```

#### 1.2 CRUD 操作实现

**文件位置**: `langflow/services/database/models/entity/crud.py`

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

class EntityCRUD:
    @staticmethod
    async def create_entity(session: AsyncSession, entity_data: EntityCreate) -> Entity:
        """创建实体"""
        entity = Entity(**entity_data.model_dump())
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity

    @staticmethod
    async def get_entities_by_space(
        session: AsyncSession,
        space_id: int,
        entity_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Entity]:
        """获取空间中的所有实体"""
        query = select(Entity).where(Entity.space_id == space_id)

        if entity_type:
            query = query.where(Entity.entity_type == entity_type)

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def search_entities_by_embedding(
        session: AsyncSession,
        space_id: int,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[Entity]:
        """通过向量相似度搜索实体"""
        # 使用 pgvector 扩展
        # SELECT *, embedding <=> $1 AS distance
        # FROM entity
        # WHERE space_id = $2
        # ORDER BY distance
        # LIMIT $3
        pass  # 具体实现依赖 pgvector

    @staticmethod
    async def get_entity_with_relations(
        session: AsyncSession,
        entity_id: int,
    ) -> tuple[Entity, list[Relation]]:
        """获取实体及其所有关系"""
        entity = await session.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # 获取出边和入边
        outgoing = select(Relation).where(Relation.source_entity_id == entity_id)
        incoming = select(Relation).where(Relation.target_entity_id == entity_id)

        outgoing_result = await session.execute(outgoing)
        incoming_result = await session.execute(incoming)

        relations = outgoing_result.scalars().all() + incoming_result.scalars().all()
        return entity, relations

    @staticmethod
    async def merge_duplicate_entities(
        session: AsyncSession,
        entity_ids: list[int],
        primary_entity_id: int,
    ) -> Entity:
        """合并重复实体"""
        # 1. 更新所有关系指向主实体
        # 2. 合并别名和属性
        # 3. 删除重复实体
        pass
```

**文件位置**: `langflow/services/database/models/relation/crud.py`

```python
class RelationCRUD:
    @staticmethod
    async def create_relation(session: AsyncSession, relation_data: RelationCreate) -> Relation:
        """创建关系"""
        relation = Relation(**relation_data.model_dump())
        session.add(relation)
        await session.commit()
        await session.refresh(relation)
        return relation

    @staticmethod
    async def get_relations_by_entity(
        session: AsyncSession,
        entity_id: int,
        direction: str = "both",  # "outgoing", "incoming", "both"
    ) -> list[Relation]:
        """获取实体的所有关系"""
        if direction == "outgoing":
            query = select(Relation).where(Relation.source_entity_id == entity_id)
        elif direction == "incoming":
            query = select(Relation).where(Relation.target_entity_id == entity_id)
        else:  # both
            query = select(Relation).where(
                (Relation.source_entity_id == entity_id) | (Relation.target_entity_id == entity_id)
            )

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_relations_by_entities(
        session: AsyncSession,
        entity_ids: list[int],
    ) -> list[Relation]:
        """获取一组实体之间的所有关系"""
        query = select(Relation).where(
            Relation.source_entity_id.in_(entity_ids),
            Relation.target_entity_id.in_(entity_ids),
        )

        result = await session.execute(query)
        return result.scalars().all()
```

---

### Phase 2: 知识构建管道融合 (第 2-4 周)

#### 2.1 扩展文档处理任务

**修改位置**: `langflow/workers/document_tasks.py`

```python
from langflow.services.knowledge.entity_extractor import EntityExtractor
from langflow.workers.entity_extraction_task import extract_entities_task

@celery_app.task(name="process_file_upload_task", queue=PRI_1)
async def process_file_upload_task(
    file_path: str,
    document_id: int,
    space_id: int,
    # ... 其他参数
):
    """处理文件上传任务 - 扩展支持图谱构建"""

    # 1. 现有流程：解析文档
    document_contents = await parse_file(file_path, ...)

    # 2. 现有流程：生成embedding
    embeddings = await generate_embeddings(document_contents)

    # 3. 现有流程：分块
    chunks = await split_into_chunks(document_contents, ...)

    # 4. 现有流程：存储到数据库
    document = await store_document(session, ...)

    # 5. ⭐ 新增：检查是否启用图谱构建
    async with get_session() as session:
        space = await session.get(Space, space_id)

        if space and space.enable_knowledge_graph and space.auto_entity_extraction:
            # 触发实体提取任务（异步，低优先级）
            extract_entities_task.apply_async(
                args=[document.id, space_id],
                queue=PRI_2,  # 低优先级队列
                countdown=5,  # 延迟5秒执行，避免与主任务冲突
            )

    return {
        "document_id": document.id,
        "chunks_count": len(chunks),
        "graph_extraction_triggered": space.enable_knowledge_graph if space else False,
    }
```

#### 2.2 实体提取任务

**新增文件**: `langflow/workers/entity_extraction_task.py`

```python
from langflow.services.knowledge.entity_extractor import EntityExtractor
from langflow.services.llm.service import LLMService
from langflow.services.database.models.entity.crud import EntityCRUD
from langflow.services.database.models.relation.crud import RelationCRUD

@celery_app.task(name="extract_entities_task", queue=PRI_2)
async def extract_entities_task(document_id: int, space_id: int):
    """从文档中提取实体和关系"""
    async with get_session() as session:
        try:
            # 1. 获取文档和chunks
            document = await session.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            chunks_query = select(Chunk).where(Chunk.document_id == document_id)
            chunks_result = await session.execute(chunks_query)
            chunks = chunks_result.scalars().all()

            # 2. 获取Space配置的LLM
            space = await session.get(Space, space_id)
            if not space or not space.graph_llm_config_id:
                logger.warning(f"No graph LLM configured for space {space_id}")
                return

            llm_service = LLMService()
            llm = await llm_service.get_llm_by_config_id(
                session,
                space.graph_llm_config_id
            )

            # 3. 提取实体（分块处理）
            entity_extractor = EntityExtractor(llm=llm)
            all_entities = []

            for chunk in chunks:
                extracted = await entity_extractor.extract_entities_from_text(
                    text=chunk.content,
                    chunk_id=chunk.id,
                    document_id=document_id,
                    space_id=space_id,
                )
                all_entities.extend(extracted)

            # 4. 实体去重和合并
            merged_entities = await entity_extractor.merge_similar_entities(
                entities=all_entities,
                similarity_threshold=0.85,
            )

            # 5. 存储实体到数据库
            created_entities = []
            for entity_data in merged_entities:
                entity = await EntityCRUD.create_entity(session, entity_data)
                created_entities.append(entity)

            # 6. 提取关系
            relations = await entity_extractor.extract_relations(
                document_content=document.content,
                entities=created_entities,
                llm=llm,
            )

            # 7. 存储关系
            created_relations = []
            for relation_data in relations:
                relation = await RelationCRUD.create_relation(session, relation_data)
                created_relations.append(relation)

            # 8. 更新 Neo4j（如果启用）
            if NEO4J_ENABLED:
                await sync_to_neo4j(
                    space_id=space_id,
                    entities=created_entities,
                    relations=created_relations,
                )

            logger.info(
                f"Extracted {len(created_entities)} entities and "
                f"{len(created_relations)} relations from document {document_id}"
            )

            return {
                "entities_count": len(created_entities),
                "relations_count": len(created_relations),
            }

        except Exception as e:
            logger.error(f"Entity extraction failed for document {document_id}: {e}")
            raise
```

#### 2.3 实体提取核心逻辑

**新增文件**: `langflow/services/knowledge/entity_extractor.py`

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

class EntityExtractor:
    """实体提取器 - 从文本中提取实体和关系"""

    def __init__(self, llm):
        self.llm = llm
        self.entity_parser = JsonOutputParser()

    async def extract_entities_from_text(
        self,
        text: str,
        chunk_id: int | None = None,
        document_id: int | None = None,
        space_id: int | None = None,
    ) -> list[EntityData]:
        """使用 LLM 提取实体"""

        # 实体提取 Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in knowledge graph construction.
Extract key entities from the text below. For each entity, provide:
- name: The entity's name
- type: Entity type (Person, Organization, Location, Concept, Event, Product, etc.)
- description: A brief description (1-2 sentences)
- aliases: Alternative names or acronyms (if any)

Return a JSON array of entities."""),
            ("user", "Text:\n{text}\n\nExtract entities:")
        ])

        # 执行提取
        chain = prompt | self.llm | self.entity_parser
        response = await chain.ainvoke({"text": text})

        # 解析结果
        entities = []
        for e in response.get("entities", []):
            # 生成实体 embedding (用于检索)
            embedding_text = f"{e['name']} {e.get('description', '')}"
            embedding = await self.generate_embedding(embedding_text)

            entities.append(EntityData(
                name=e["name"],
                entity_type=e["type"],
                description=e.get("description"),
                aliases=e.get("aliases", []),
                embedding=embedding,
                chunk_id=chunk_id,
                document_id=document_id,
                space_id=space_id,
            ))

        return entities

    async def extract_relations(
        self,
        document_content: str,
        entities: list[Entity],
        llm,
    ) -> list[RelationData]:
        """提取实体之间的关系"""

        # 构建实体列表文本
        entity_list = "\n".join([
            f"{i+1}. {e.name} ({e.entity_type})"
            for i, e in enumerate(entities)
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in knowledge graph construction.
Given a list of entities and a document, identify relationships between them.
For each relationship, provide:
- source: Source entity name
- target: Target entity name
- type: Relationship type (PartOf, LeadsTo, RelatedTo, CreatedBy, etc.)
- description: Brief description of the relationship
- weight: Confidence score (0.0-1.0)

Return a JSON array of relationships."""),
            ("user", """Entities:
{entity_list}

Document:
{document}

Extract relationships:""")
        ])

        chain = prompt | llm | JsonOutputParser()
        response = await chain.ainvoke({
            "entity_list": entity_list,
            "document": document_content[:5000],  # 限制长度
        })

        # 将实体名映射到ID
        entity_map = {e.name.lower(): e.id for e in entities}

        relations = []
        for r in response.get("relationships", []):
            source_id = entity_map.get(r["source"].lower())
            target_id = entity_map.get(r["target"].lower())

            if source_id and target_id:
                relations.append(RelationData(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relation_type=r["type"],
                    description=r.get("description"),
                    weight=r.get("weight", 1.0),
                    space_id=entities[0].space_id,
                    document_id=entities[0].document_id,
                ))

        return relations

    async def merge_similar_entities(
        self,
        entities: list[EntityData],
        similarity_threshold: float = 0.85,
    ) -> list[EntityData]:
        """合并相似实体（去重）"""
        # 使用 embedding 相似度计算
        # 1. 计算所有实体对之间的余弦相似度
        # 2. 将相似度 > threshold 的实体合并
        # 3. 合并时保留描述更详细的实体，合并别名
        pass  # 具体实现

    async def generate_embedding(self, text: str) -> list[float]:
        """生成文本的向量嵌入"""
        # 使用与 Document/Chunk 相同的 embedding 服务
        from langflow.services.embeddings import get_embedding_service
        service = get_embedding_service()
        return await service.embed_query(text)
```

---

### Phase 3: 语义查询融合 (第 5-7.5 周)

#### 3.1 统一搜索 API

**新增/扩展文件**: `langflow/api/v1/search.py`

```python
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/")
async def unified_search(
    query: str,
    space_id: int,
    mode: str = "hybrid",  # "document", "entity", "hybrid"
    top_k: int = 10,
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """
    统一搜索接口 - 同时搜索文档和实体

    Args:
        query: 搜索查询
        space_id: 空间ID
        mode: 搜索模式 (document=仅文档, entity=仅实体, hybrid=混合)
        top_k: 返回结果数量
        filters: 额外过滤条件

    Returns:
        {
            "documents": [...],  # 文档结果
            "entities": [...],   # 实体结果
            "relations": [...],  # 相关关系
        }
    """
    results = {"documents": [], "entities": [], "relations": []}

    # 1. 文档检索
    if mode in ["document", "hybrid"]:
        # 使用现有的文档混合检索（向量 + 全文）
        from langflow.services.retrieval import DocumentHybridSearchRetriever

        documents = await DocumentHybridSearchRetriever.search(
            session=session,
            query=query,
            space_id=space_id,
            top_k=top_k,
        )
        results["documents"] = [doc.to_dict() for doc in documents]

    # 2. 实体检索
    if mode in ["entity", "hybrid"]:
        # 生成查询 embedding
        from langflow.services.embeddings import get_embedding_service
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_query(query)

        # 向量相似度搜索实体
        entities = await EntityCRUD.search_entities_by_embedding(
            session=session,
            space_id=space_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        results["entities"] = [entity.to_dict() for entity in entities]

        # 获取实体之间的关系
        entity_ids = [e.id for e in entities]
        relations = await RelationCRUD.get_relations_by_entities(
            session=session,
            entity_ids=entity_ids,
        )

        results["relations"] = [rel.to_dict() for rel in relations]

    return results
```

#### 3.2 实体 API

**新增文件**: `langflow/api/v1/entities.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/entities", tags=["entities"])

@router.get("/")
async def list_entities(
    space_id: int,
    entity_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """获取实体列表"""
    # 检查权限
    await check_space_permission(session, space_id, current_user.id)

    entities = await EntityCRUD.get_entities_by_space(
        session=session,
        space_id=space_id,
        entity_type=entity_type,
        page=page,
        page_size=page_size,
    )

    return {
        "entities": [e.to_dict() for e in entities],
        "page": page,
        "page_size": page_size,
        "total": len(entities),  # TODO: 实现总数查询
    }

@router.get("/{entity_id}")
async def get_entity_details(
    entity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """获取实体详情（包含相关文档和关系）"""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # 检查权限
    await check_space_permission(session, entity.space_id, current_user.id)

    # 获取相关文档
    related_docs = []
    if entity.document_id:
        doc = await session.get(Document, entity.document_id)
        if doc:
            related_docs.append(doc.to_dict())

    # 获取关系
    relations = await RelationCRUD.get_relations_by_entity(
        session=session,
        entity_id=entity_id,
    )

    # 获取关系中的其他实体
    related_entity_ids = set()
    for rel in relations:
        related_entity_ids.add(rel.source_entity_id)
        related_entity_ids.add(rel.target_entity_id)
    related_entity_ids.discard(entity_id)

    related_entities = []
    for eid in related_entity_ids:
        e = await session.get(Entity, eid)
        if e:
            related_entities.append(e.to_dict())

    return {
        "entity": entity.to_dict(),
        "related_documents": related_docs,
        "relations": [r.to_dict() for r in relations],
        "related_entities": related_entities,
    }

@router.put("/{entity_id}")
async def update_entity(
    entity_id: int,
    entity_update: EntityUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """更新实体（人工校正）"""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    await check_space_permission(session, entity.space_id, current_user.id)

    # 更新字段
    for field, value in entity_update.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)

    entity.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(entity)

    return entity.to_dict()

@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """删除实体"""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    await check_space_permission(session, entity.space_id, current_user.id)

    # 删除相关关系
    await session.execute(
        delete(Relation).where(
            (Relation.source_entity_id == entity_id) | (Relation.target_entity_id == entity_id)
        )
    )

    # 删除实体
    await session.delete(entity)
    await session.commit()

    return {"message": "Entity deleted successfully"}
```

#### 3.3 图谱查询 API

**新增文件**: `langflow/api/v1/graphs.py`

```python
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/graphs", tags=["graphs"])

@router.get("/{space_id}/subgraph")
async def get_subgraph(
    space_id: int,
    entity_ids: list[int] | None = None,
    max_depth: int = 2,
    max_nodes: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """
    获取子图 (用于可视化)

    Args:
        space_id: 空间ID
        entity_ids: 起始实体ID列表 (如果为空则返回空间的完整图)
        max_depth: 最大遍历深度
        max_nodes: 最大节点数

    Returns:
        {
            "nodes": [...],  # 实体节点
            "edges": [...],  # 关系边
        }
    """
    await check_space_permission(session, space_id, current_user.id)

    if entity_ids:
        # 基于给定实体扩展子图 (BFS遍历)
        subgraph = await build_subgraph_from_entities(
            session=session,
            entity_ids=entity_ids,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    else:
        # 返回空间的完整图（限制节点数）
        subgraph = await get_full_graph(
            session=session,
            space_id=space_id,
            max_nodes=max_nodes,
        )

    return {
        "nodes": [e.to_dict() for e in subgraph["entities"]],
        "edges": [r.to_dict() for r in subgraph["relations"]],
    }

@router.post("/{space_id}/traverse")
async def traverse_graph(
    space_id: int,
    start_entity_id: int,
    relation_types: list[str] | None = None,
    max_depth: int = 3,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """
    图遍历 (BFS/DFS)

    Args:
        space_id: 空间ID
        start_entity_id: 起始实体ID
        relation_types: 关系类型过滤
        max_depth: 最大遍历深度

    Returns:
        遍历路径和发现的实体
    """
    await check_space_permission(session, space_id, current_user.id)

    result = await graph_traverse_bfs(
        session=session,
        start_entity_id=start_entity_id,
        relation_types=relation_types,
        max_depth=max_depth,
    )

    return result

async def build_subgraph_from_entities(
    session: AsyncSession,
    entity_ids: list[int],
    max_depth: int,
    max_nodes: int,
) -> dict:
    """从给定实体扩展子图"""
    visited_entities = set(entity_ids)
    visited_relations = set()
    entities = []
    relations = []

    # BFS 遍历
    queue = [(eid, 0) for eid in entity_ids]  # (entity_id, depth)

    while queue and len(visited_entities) < max_nodes:
        entity_id, depth = queue.pop(0)

        if depth >= max_depth:
            continue

        # 获取实体
        entity = await session.get(Entity, entity_id)
        if entity:
            entities.append(entity)

        # 获取关系
        rels = await RelationCRUD.get_relations_by_entity(session, entity_id)

        for rel in rels:
            if rel.id not in visited_relations:
                visited_relations.add(rel.id)
                relations.append(rel)

                # 添加邻居实体到队列
                neighbor_id = (
                    rel.target_entity_id if rel.source_entity_id == entity_id
                    else rel.source_entity_id
                )

                if neighbor_id not in visited_entities:
                    visited_entities.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

    return {"entities": entities, "relations": relations}

async def graph_traverse_bfs(
    session: AsyncSession,
    start_entity_id: int,
    relation_types: list[str] | None,
    max_depth: int,
) -> dict:
    """BFS 图遍历"""
    # 类似 build_subgraph_from_entities 但返回路径信息
    pass
```

---

### Phase 4: 前端融合 (第 8-11.5 周)

#### 4.1 图谱可视化组件 (React)

**新增目录**: `langflow/src/frontend/src/components/knowledgeGraph/`

```
knowledgeGraph/
├── KnowledgeGraphView.tsx      # 主可视化组件 (G6渲染)
├── GraphControls.tsx           # 控件 (缩放、布局、过滤)
├── EntityPanel.tsx             # 实体详情面板
├── EntityList.tsx              # 实体列表
├── RelationFilter.tsx          # 关系过滤器
└── useGraphData.ts             # 数据钩子
```

**KnowledgeGraphView.tsx**:

```tsx
import { Graph } from '@antv/g6';
import { useEffect, useRef, useState } from 'react';
import { useDarkStore } from '@/stores/darkStore';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  label?: string;
}

interface KnowledgeGraphViewProps {
  spaceId: number;
  selectedEntityIds?: number[];
  onNodeClick?: (nodeId: string) => void;
}

export const KnowledgeGraphView = ({
  spaceId,
  selectedEntityIds = [],
  onNodeClick,
}: KnowledgeGraphViewProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const { dark } = useDarkStore();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 初始化 G6 图谱
    const graph = new Graph({
      container: containerRef.current,
      width: containerRef.current.offsetWidth,
      height: containerRef.current.offsetHeight,
      modes: {
        default: [
          'drag-canvas',
          'zoom-canvas',
          'drag-node',
          {
            type: 'click-select',
            multiple: true,
          },
        ],
      },
      layout: {
        type: 'force',  // 力导向布局
        preventOverlap: true,
        nodeSize: 40,
        linkDistance: 150,
        nodeStrength: -30,
        edgeStrength: 0.1,
      },
      defaultNode: {
        size: 40,
        style: {
          fill: dark ? '#4B5563' : '#E5E7EB',
          stroke: dark ? '#9CA3AF' : '#6B7280',
          lineWidth: 2,
        },
        labelCfg: {
          position: 'bottom',
          offset: 10,
          style: {
            fill: dark ? '#F3F4F6' : '#1F2937',
            fontSize: 12,
          },
        },
      },
      defaultEdge: {
        type: 'line',
        style: {
          stroke: dark ? '#4B5563' : '#D1D5DB',
          lineWidth: 1,
          endArrow: {
            path: 'M 0,0 L 8,4 L 8,-4 Z',
            fill: dark ? '#4B5563' : '#D1D5DB',
          },
        },
        labelCfg: {
          autoRotate: true,
          style: {
            fill: dark ? '#9CA3AF' : '#6B7280',
            fontSize: 10,
          },
        },
      },
    });

    // 节点点击事件
    graph.on('node:click', (evt) => {
      const node = evt.item;
      if (node && onNodeClick) {
        onNodeClick(node.getID());
      }
    });

    // 加载图谱数据
    const loadGraphData = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          max_depth: '2',
          max_nodes: '100',
        });

        if (selectedEntityIds.length > 0) {
          params.set('entity_ids', selectedEntityIds.join(','));
        }

        const response = await fetch(
          `/api/v1/graphs/${spaceId}/subgraph?${params}`
        );

        if (!response.ok) {
          throw new Error('Failed to load graph data');
        }

        const data = await response.json();

        // 转换为 G6 格式
        const g6Data = {
          nodes: data.nodes.map((entity: any) => ({
            id: String(entity.id),
            label: entity.name,
            type: entity.entity_type,
          })),
          edges: data.edges.map((relation: any) => ({
            source: String(relation.source_entity_id),
            target: String(relation.target_entity_id),
            label: relation.relation_type,
          })),
        };

        graph.data(g6Data);
        graph.render();
        graph.fitView(20);  // 自适应视口，留20px边距

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    loadGraphData();
    graphRef.current = graph;

    // 窗口大小变化时重新渲染
    const handleResize = () => {
      if (containerRef.current && graph) {
        graph.changeSize(
          containerRef.current.offsetWidth,
          containerRef.current.offsetHeight
        );
        graph.fitView(20);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      graph.destroy();
    };
  }, [spaceId, selectedEntityIds, dark, onNodeClick]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  return <div ref={containerRef} className="w-full h-full" />;
};
```

**GraphControls.tsx**:

```tsx
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  layout: string;
  onLayoutChange: (layout: string) => void;
}

export const GraphControls = ({
  onZoomIn,
  onZoomOut,
  onFitView,
  layout,
  onLayoutChange,
}: GraphControlsProps) => {
  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 bg-white dark:bg-gray-800 p-2 rounded-md shadow-md">
      <Button size="sm" onClick={onZoomIn}>
        Zoom In
      </Button>
      <Button size="sm" onClick={onZoomOut}>
        Zoom Out
      </Button>
      <Button size="sm" onClick={onFitView}>
        Fit View
      </Button>

      <Select value={layout} onValueChange={onLayoutChange}>
        <SelectTrigger>
          <span>Layout: {layout}</span>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="force">Force</SelectItem>
          <SelectItem value="circular">Circular</SelectItem>
          <SelectItem value="radial">Radial</SelectItem>
          <SelectItem value="dagre">Dagre</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};
```

**EntityPanel.tsx**:

```tsx
import { useQuery } from 'react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface EntityPanelProps {
  entityId: string | null;
}

export const EntityPanel = ({ entityId }: EntityPanelProps) => {
  const { data, isLoading } = useQuery(
    ['entity', entityId],
    async () => {
      if (!entityId) return null;
      const response = await fetch(`/api/v1/entities/${entityId}`);
      return response.json();
    },
    { enabled: !!entityId }
  );

  if (!entityId) {
    return (
      <div className="p-4 text-gray-500">
        Select a node to view details
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-4">Loading...</div>;
  }

  const entity = data?.entity;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{entity?.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div>
            <span className="font-semibold">Type:</span> {entity?.entity_type}
          </div>
          <div>
            <span className="font-semibold">Description:</span> {entity?.description}
          </div>

          {entity?.aliases && entity.aliases.length > 0 && (
            <div>
              <span className="font-semibold">Aliases:</span>{' '}
              {entity.aliases.join(', ')}
            </div>
          )}

          {data?.relations && data.relations.length > 0 && (
            <div>
              <span className="font-semibold">Relations:</span>
              <ul className="list-disc list-inside mt-1">
                {data.relations.map((rel: any) => (
                  <li key={rel.id}>
                    {rel.relation_type} → {rel.target_entity_id}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data?.related_documents && data.related_documents.length > 0 && (
            <div>
              <span className="font-semibold">Source Documents:</span>
              <ul className="list-disc list-inside mt-1">
                {data.related_documents.map((doc: any) => (
                  <li key={doc.id}>{doc.title}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
```

#### 4.2 扩展知识库页面

**修改文件**: `langflow/src/frontend/src/pages/MainPage/pages/knowledgePage/index.tsx`

```tsx
import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { KnowledgeGraphView } from '@/components/knowledgeGraph/KnowledgeGraphView';
import { EntityBrowser } from '@/components/knowledgeGraph/EntityBrowser';
import { UnifiedSearch } from '@/components/UnifiedSearch';

export const KnowledgePage = () => {
  const [activeTab, setActiveTab] = useState<'documents' | 'graph' | 'entities'>('documents');
  const [selectedSpace, setSelectedSpace] = useState<number | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  return (
    <div className="knowledge-page h-full flex flex-col">
      {/* 顶部：统一搜索框 */}
      <div className="p-4 border-b">
        <UnifiedSearch spaceId={selectedSpace} />
      </div>

      {/* Tab 切换 */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1">
        <div className="border-b px-4">
          <TabsList>
            <TabsTrigger value="documents">📄 Documents</TabsTrigger>
            <TabsTrigger value="entities">🏷️ Entities</TabsTrigger>
            <TabsTrigger value="graph">🕸️ Knowledge Graph</TabsTrigger>
          </TabsList>
        </div>

        {/* 文档 Tab (现有) */}
        <TabsContent value="documents" className="flex-1">
          <KnowledgeBasesTab
            spaceId={selectedSpace}
            onSpaceChange={setSelectedSpace}
          />
        </TabsContent>

        {/* 实体 Tab (新增) */}
        <TabsContent value="entities" className="flex-1">
          <EntityBrowser
            spaceId={selectedSpace}
            onEntitySelect={setSelectedEntityId}
          />
        </TabsContent>

        {/* 图谱 Tab (新增) */}
        <TabsContent value="graph" className="flex-1 p-4">
          <div className="grid grid-cols-3 gap-4 h-full">
            {/* 左侧：图谱可视化 */}
            <div className="col-span-2 border rounded-md relative">
              <KnowledgeGraphView
                spaceId={selectedSpace}
                onNodeClick={setSelectedEntityId}
              />
            </div>

            {/* 右侧：实体详情面板 */}
            <div className="border rounded-md overflow-auto">
              <EntityPanel entityId={selectedEntityId} />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};
```

#### 4.3 统一搜索面板

**新增组件**: `langflow/src/frontend/src/components/UnifiedSearch.tsx`

```tsx
import { useState } from 'react';
import { useQuery } from 'react-query';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select';

interface UnifiedSearchProps {
  spaceId: number | null;
}

export const UnifiedSearch = ({ spaceId }: UnifiedSearchProps) => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'hybrid' | 'document' | 'entity'>('hybrid');

  const { data: results, isLoading } = useQuery(
    ['unified-search', spaceId, query, mode],
    async () => {
      if (!spaceId || !query) return null;

      const response = await fetch('/api/v1/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          space_id: spaceId,
          mode,
          top_k: 10,
        }),
      });

      return response.json();
    },
    { enabled: !!spaceId && !!query }
  );

  return (
    <div className="space-y-4">
      {/* 搜索框和模式选择 */}
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents and entities..."
          className="flex-1"
        />

        <Select value={mode} onValueChange={(v) => setMode(v as any)}>
          <SelectTrigger className="w-48">
            <span>{mode === 'hybrid' ? 'Hybrid' : mode === 'document' ? 'Documents' : 'Entities'}</span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="hybrid">Hybrid (Documents + Entities)</SelectItem>
            <SelectItem value="document">Documents Only</SelectItem>
            <SelectItem value="entity">Entities Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 结果展示 */}
      {isLoading && <div className="text-gray-500">Searching...</div>}

      {results && (
        <div className="space-y-4">
          {/* 文档结果 */}
          {results.documents && results.documents.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Documents ({results.documents.length})</h3>
              <div className="space-y-2">
                {results.documents.map((doc: any) => (
                  <DocumentCard key={doc.id} document={doc} />
                ))}
              </div>
            </div>
          )}

          {/* 实体结果 */}
          {results.entities && results.entities.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Entities ({results.entities.length})</h3>
              <div className="space-y-2">
                {results.entities.map((entity: any) => (
                  <EntityCard key={entity.id} entity={entity} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## 四、时间和资源估算

### 4.1 详细工时分解

| 阶段 | 任务 | 工时 | 周数 (2人) |
|------|------|------|-----------|
| **Phase 1** | 数据模型融合 | 80-100h | 1-1.5 周 |
| 1.1 | 新增 Entity/Relation 表 | 20-25h | 0.5 周 |
| 1.2 | CRUD 操作实现 | 25-30h | 0.5 周 |
| 1.3 | 数据库迁移测试 | 15-20h | 0.25 周 |
| 1.4 | Neo4j 集成 (可选) | 20-25h | 0.25 周 |
| **Phase 2** | 知识构建管道融合 | 120-160h | 2-3 周 |
| 2.1 | 扩展文档处理任务 | 30-40h | 0.5 周 |
| 2.2 | 实体提取任务 | 40-50h | 1 周 |
| 2.3 | 关系提取逻辑 | 30-40h | 0.5 周 |
| 2.4 | 去重和合并算法 | 20-30h | 0.5 周 |
| **Phase 3** | 语义查询融合 | 100-130h | 2-2.5 周 |
| 3.1 | 统一搜索 API | 40-50h | 1 周 |
| 3.2 | 实体 API | 30-40h | 0.5 周 |
| 3.3 | 图谱查询 API | 30-40h | 0.5 周 |
| **Phase 4** | 前端融合 | 160-200h | 3-4 周 |
| 4.1 | 图谱可视化组件 | 80-100h | 2 周 |
| 4.2 | 扩展知识库页面 | 40-50h | 1 周 |
| 4.3 | 统一搜索面板 | 40-50h | 1 周 |
| **Phase 5** | 测试和优化 | 80-100h | 1.5-2 周 |
| 5.1 | 单元测试 | 30-40h | 0.5 周 |
| 5.2 | 集成测试 | 30-40h | 0.5 周 |
| 5.3 | 性能优化 | 20-20h | 0.5 周 |
| **总计** | | **540-690h** | **10.5-13 周** |

### 4.2 里程碑

- **M1 (2周)**: 数据模型就绪，可创建实体/关系
- **M2 (5周)**: 知识构建管道完成，文档上传自动提取实体
- **M3 (7.5周)**: API 层完成，可通过 API 查询实体和图谱
- **M4 (11.5周)**: 前端完成，用户可在 UI 中查看图谱
- **M5 (13周)**: 测试通过，生产就绪

---

## 五、风险与缓解

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| LLM 提取质量不稳定 | 高 | 提供人工校正接口，允许用户编辑实体 |
| 实体去重算法效果差 | 中 | 使用 embedding 相似度 + 人工审核 |
| 图谱性能问题（大规模数据） | 中 | 限制可视化节点数量，使用分页 |
| 前端 Vue→React 迁移困难 | 低 | G6 配置保持不变，只迁移状态管理 |
| Neo4j 额外依赖 | 低 | 先用 PostgreSQL，Neo4j 作为可选优化 |
| 权限管理复杂性 | 中 | 继承 Space 的 RBAC 权限，保持一致性 |

---

## 六、验收标准

### 6.1 功能验收

- [ ] ✅ 文档上传后自动提取实体和关系
- [ ] ✅ 可通过 API 查询实体列表和详情
- [ ] ✅ 可通过 API 获取图谱数据
- [ ] ✅ 前端可可视化知识图谱 (G6)
- [ ] ✅ 统一搜索可同时查询文档和实体
- [ ] ✅ 实体可链接到来源文档
- [ ] ✅ 支持图谱遍历 (BFS/DFS)
- [ ] ✅ 用户可手动编辑实体和关系

### 6.2 性能验收

- [ ] 1000文档的实体提取 < 10分钟 (并行处理)
- [ ] 实体检索响应时间 < 1秒
- [ ] 图谱可视化渲染 < 1秒 (100节点)
- [ ] 统一搜索响应时间 < 2秒

### 6.3 质量验收

- [ ] 单元测试覆盖率 > 70%
- [ ] API 集成测试通过
- [ ] 前端 E2E 测试通过
- [ ] RBAC 权限正确实施
- [ ] 文档完整（API文档 + 用户指南）

---

## 七、关键技术迁移

### 7.1 从 Yuxi-Know 迁移的核心代码

**1. 实体提取逻辑**
- 源文件: `/Users/jiangwei/Python/Yuxi-Know/src/knowledge/indexing.py`
- 目标文件: `langflow/services/knowledge/entity_extractor.py`
- 迁移内容:
  - `extract_entities_from_text()` - LLM提取实体
  - `merge_similar_entities()` - 实体去重
  - `extract_relations()` - 关系提取

**2. 图谱可视化适配器**
- 源文件: `/Users/jiangwei/Python/Yuxi-Know/src/knowledge/adapters/lightrag_to_graph.py`
- 目标文件: `langflow/services/knowledge/graph_adapter.py`
- 迁移内容:
  - 实体→G6节点转换
  - 关系→G6边转换
  - 图谱布局配置

**3. Vue → React 组件迁移**
- 源文件: `/Users/jiangwei/Python/Yuxi-Know/web/src/components/Graph/KnowledgeGraph.vue`
- 目标文件: `langflow/src/frontend/src/components/knowledgeGraph/KnowledgeGraphView.tsx`
- 迁移内容:
  - G6 初始化逻辑 (保持不变)
  - 交互事件处理 (Vue → React Hooks)
  - 状态管理 (Vue → Zustand)

---

## 八、下一步行动

### 8.1 立即可做 (无需审批)

1. **创建数据库迁移文件**
   - 定义 Entity/Relation 表结构
   - 编写 Alembic 迁移

2. **实现 CRUD 操作**
   - EntityCRUD, RelationCRUD
   - 单元测试

3. **设计 API 接口规范**
   - `/api/v1/entities`
   - `/api/v1/graphs`
   - `/api/v1/search` (扩展)

### 8.2 需要决策的问题

**Q1: Neo4j 是否必需？**
- 推荐：先用 PostgreSQL + JSON 字段存储图谱，性能不足再上 Neo4j
- 优势：减少依赖，开发更快
- 劣势：图遍历性能较差

**Q2: 实体提取策略？**
- 选项A: 纯LLM提取 (简单，质量高，成本高)
- 选项B: NER模型 + LLM (快速，需训练)
- 推荐：先用LLM，后续可切换

**Q3: 前端图可视化库？**
- 推荐：AntV G6 (与 Yuxi-Know 一致，迁移简单)
- 备选：Cytoscape.js (轻量)

**Q4: 渐进式发布？**
- 推荐：Beta 功能开关 (Space 级别配置)
- 优势：可灰度测试，降低风险

---

## 九、总结

**融合方案核心优势**：

✅ **真正融合**：图谱能力深度集成到 SurfSense 每个环节
✅ **用户无感知**：文档上传自动构建图谱，无需额外操作
✅ **统一体验**：单一搜索框同时查询文档和实体
✅ **渐进式启用**：Space 级别配置，可选择性启用图谱功能
✅ **代码复用**：利用现有 Document/Chunk 处理管道
✅ **最小依赖**：先用 PostgreSQL，Neo4j 可选

**预期效果**: SurfSense 用户获得世界级的知识图谱能力，体验无缝、流畅。

---

**文档生成时间**: 2026-01-04
**作者**: Claude Code AI Assistant
**版本**: 1.0
