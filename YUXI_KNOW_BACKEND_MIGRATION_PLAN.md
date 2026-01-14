# Yuxi-Know 图谱知识库后端迁移到 SurfSense 方案

## 执行摘要

本文档描述了将 Yuxi-Know 项目的**图谱知识库后端能力**（语义查询 + 知识构建）深度融合到 SurfSense 后端的完整实施方案。

**核心目标**:
- ✅ 后端图谱能力集成（实体提取、关系构建、图谱存储）
- ✅ 语义查询 API (LightRAG 混合检索：向量+图谱)
- ✅ 知识构建管道（文档上传自动提取实体）
- ✅ 真正融合，深度集成到现有文档处理流程
- ⏸️ 前端迁移暂缓（后续单独规划）

**预计工时**: 300-390 小时 (6-8 周，2人团队) - 仅后端部分

**技术栈**:
- 后端: Python + FastAPI + SQLModel + PostgreSQL
- 检索: LightRAG (向量 + 图谱混合)
- 异步处理: Celery + Redis
- 可选: Neo4j (图谱优化)

---

## 一、项目背景分析

### 1.1 Yuxi-Know 后端核心能力

**需要迁移的后端功能**:
- 图谱知识库系统 (~3,000 行)
- 语义查询接口 (~500 行)
- 知识构建管道 (~1,000 行)

**核心技术实现**:
```python
# Yuxi-Know 核心后端文件
/Users/jiangwei/Python/Yuxi-Know/
├── src/knowledge/implementations/lightrag.py    # LightRAG 实现
├── src/knowledge/adapters/lightrag_to_graph.py  # 图谱适配器
├── src/knowledge/indexing.py                    # 实体提取
└── src/api/                                      # REST API
```

### 1.2 SurfSense 现有后端架构

**已有基础**:
```
langflow/src/backend/base/langflow/
├── services/database/models/
│   ├── document/model.py          ✅ 文档模型 (支持embedding)
│   ├── chunk/model.py             ✅ 文本块模型 (支持embedding)
│   ├── connector/model.py         ✅ 15个数据源连接器
│   └── space/model.py             ✅ 空间隔离
│
├── api/v1/
│   ├── documents.py               ✅ 文档CRUD + 搜索
│   ├── connectors.py              ✅ 连接器管理 + 索引任务
│   └── knowledge_bases.py         ✅ 知识库元数据
│
├── services/
│   ├── query/service.py           ✅ 查询重构 (用LLM优化)
│   └── docling/                   ✅ 文档解析
│
└── workers/
    ├── document_tasks.py          ✅ 后台文档处理
    └── connector_tasks.py         ✅ 连接器索引任务
```

**关键缺失**:
- ❌ Entity/Relation 数据模型
- ❌ 实体/关系提取管道
- ❌ 图谱查询 API
- ❌ LightRAG 集成

**现有搜索的局限性**:
```python
# 当前 documents.py 的搜索 (第 359 行)
query = query.filter(Document.title.ilike(f"%{title}%"))
# ⚠️ 仅支持标题模糊匹配，无语义搜索
```

---

## 二、后端融合架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│              SurfSense 后端融合图谱后架构                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【处理管道】 (融合点 1: 文档索引)                           │
│  ├── 文档上传/连接器导入                                      │
│  ├── ├─→ 解析 (Docling)                    ✅ 现有         │
│  ├── ├─→ 分块 (Chonkie)                    ✅ 现有         │
│  ├── ├─→ Embedding (OpenAI/Cohere)         ✅ 现有         │
│  ├── ├─→ [新] 实体提取 (LLM)               ⭐ 新增         │
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
│  ├── /api/v1/documents                     ✅ 现有         │
│  ├── [新] /api/v1/entities                 ⭐ 新增         │
│  ├── [新] /api/v1/graphs                   ⭐ 新增         │
│  └── [扩展] /api/v1/search?mode=hybrid     ⭐ 扩展         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 融合原则

1. **数据融合**: Entity/Relation 与 Document/Chunk 在同一数据库，通过外键关联
2. **流程融合**: 文档上传时自动触发实体提取，无需用户额外操作
3. **检索融合**: 单一搜索接口同时返回文档和实体结果
4. **权限融合**: Entity/Relation 继承 Space 的 RBAC 权限

---

## 三、后端实施方案

### Phase 1: 数据模型融合 (第 1-1.5 周)

#### 1.1 新增数据库表

**迁移文件**: `src/backend/base/langflow/alembic/versions/xxx_add_knowledge_graph_tables.py`

**Entity 表结构**:

```python
from sqlmodel import SQLModel, Field, Column, JSON
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
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSON))

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

**扩展 Space 表**:

```python
# 在现有 Space 模型中添加字段
# 文件: src/backend/base/langflow/services/database/models/space/model.py

class Space(SQLModel, table=True):
    # ... 现有字段 ...

    # 新增：图谱配置
    enable_knowledge_graph: bool = Field(default=False)  # 是否启用图谱构建
    graph_llm_config_id: int | None = Field(default=None, foreign_key="llm_config.id")
    auto_entity_extraction: bool = Field(default=True)  # 是否自动提取实体
```

#### 1.2 CRUD 操作实现

**目录结构**:
```
src/backend/base/langflow/services/database/models/
├── entity/
│   ├── __init__.py
│   ├── model.py          # Entity 模型
│   └── crud.py           # EntityCRUD
└── relation/
    ├── __init__.py
    ├── model.py          # Relation 模型
    └── crud.py           # RelationCRUD
```

**EntityCRUD 实现**:

```python
# src/backend/base/langflow/services/database/models/entity/crud.py

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from langflow.services.database.models.entity.model import Entity

class EntityCRUD:
    @staticmethod
    async def create_entity(session: AsyncSession, entity_data: dict) -> Entity:
        """创建实体"""
        entity = Entity(**entity_data)
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
        """通过向量相似度搜索实体

        使用 pgvector 扩展进行向量搜索
        """
        # TODO: 使用 pgvector 的向量相似度搜索
        # 示例 SQL:
        # SELECT *, embedding <=> $1 AS distance
        # FROM entity
        # WHERE space_id = $2
        # ORDER BY distance
        # LIMIT $3
        pass

    @staticmethod
    async def get_entity_with_relations(
        session: AsyncSession,
        entity_id: int,
    ) -> tuple[Entity, list]:
        """获取实体及其所有关系"""
        from langflow.services.database.models.relation.model import Relation

        entity = await session.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # 获取出边和入边
        outgoing = select(Relation).where(Relation.source_entity_id == entity_id)
        incoming = select(Relation).where(Relation.target_entity_id == entity_id)

        outgoing_result = await session.execute(outgoing)
        incoming_result = await session.execute(incoming)

        relations = list(outgoing_result.scalars().all()) + list(incoming_result.scalars().all())
        return entity, relations

    @staticmethod
    async def update_entity(
        session: AsyncSession,
        entity_id: int,
        update_data: dict,
    ) -> Entity:
        """更新实体"""
        entity = await session.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        for field, value in update_data.items():
            setattr(entity, field, value)

        entity.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(entity)
        return entity

    @staticmethod
    async def delete_entity(session: AsyncSession, entity_id: int) -> None:
        """删除实体及其关系"""
        from langflow.services.database.models.relation.model import Relation
        from sqlmodel import delete

        # 删除相关关系
        await session.execute(
            delete(Relation).where(
                (Relation.source_entity_id == entity_id) | (Relation.target_entity_id == entity_id)
            )
        )

        # 删除实体
        entity = await session.get(Entity, entity_id)
        if entity:
            await session.delete(entity)
            await session.commit()
```

**RelationCRUD 实现**:

```python
# src/backend/base/langflow/services/database/models/relation/crud.py

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from langflow.services.database.models.relation.model import Relation

class RelationCRUD:
    @staticmethod
    async def create_relation(session: AsyncSession, relation_data: dict) -> Relation:
        """创建关系"""
        relation = Relation(**relation_data)
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

    @staticmethod
    async def delete_relation(session: AsyncSession, relation_id: int) -> None:
        """删除关系"""
        relation = await session.get(Relation, relation_id)
        if relation:
            await session.delete(relation)
            await session.commit()
```

---

### Phase 2: 知识构建管道融合 (第 2-4 周)

#### 2.1 扩展文档处理任务

**修改位置**: `src/backend/base/langflow/workers/document_tasks.py`

```python
from langflow.workers.entity_extraction_task import extract_entities_task

@celery_app.task(name="process_file_upload_task", queue=PRI_1)
async def process_file_upload_task(
    file_path: str,
    document_id: int,
    space_id: int,
    # ... 其他参数
):
    """处理文件上传任务 - 扩展支持图谱构建"""

    # 1-4. 现有流程：解析、embedding、分块、存储
    # ... (现有代码保持不变)

    # 5. ⭐ 新增：检查是否启用图谱构建
    async with get_session() as session:
        space = await session.get(Space, space_id)

        if space and space.enable_knowledge_graph and space.auto_entity_extraction:
            # 触发实体提取任务（异步，低优先级）
            extract_entities_task.apply_async(
                args=[document_id, space_id],
                queue=PRI_2,  # 低优先级队列
                countdown=5,  # 延迟5秒执行
            )

    return {
        "document_id": document_id,
        "chunks_count": len(chunks),
        "graph_extraction_triggered": (
            space.enable_knowledge_graph if space else False
        ),
    }
```

#### 2.2 实体提取任务

**新增文件**: `src/backend/base/langflow/workers/entity_extraction_task.py`

```python
from celery import current_app as celery_app
from langflow.services.database.utils import get_session
from langflow.services.database.models.document.model import Document
from langflow.services.database.models.chunk.model import Chunk
from langflow.services.database.models.space.model import Space
from langflow.services.database.models.entity.crud import EntityCRUD
from langflow.services.database.models.relation.crud import RelationCRUD
from langflow.services.knowledge.entity_extractor import EntityExtractor
from langflow.services.llm.service import LLMService
from sqlmodel import select
import logging

logger = logging.getLogger(__name__)

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
            # TODO: Neo4j 集成

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

**新增文件**: `src/backend/base/langflow/services/knowledge/entity_extractor.py`

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
import logging

logger = logging.getLogger(__name__)

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
    ) -> list[dict]:
        """使用 LLM 提取实体"""

        # 实体提取 Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in knowledge graph construction.
Extract key entities from the text below. For each entity, provide:
- name: The entity's name
- type: Entity type (Person, Organization, Location, Concept, Event, Product, etc.)
- description: A brief description (1-2 sentences)
- aliases: Alternative names or acronyms (if any)

Return a JSON object with an "entities" array."""),
            ("user", "Text:\n{text}\n\nExtract entities:")
        ])

        # 执行提取
        try:
            chain = prompt | self.llm | self.entity_parser
            response = await chain.ainvoke({"text": text})

            # 解析结果
            entities = []
            for e in response.get("entities", []):
                # 生成实体 embedding (用于检索)
                embedding_text = f"{e['name']} {e.get('description', '')}"
                embedding = await self.generate_embedding(embedding_text)

                entities.append({
                    "name": e["name"],
                    "entity_type": e["type"],
                    "description": e.get("description"),
                    "aliases": e.get("aliases", []),
                    "embedding": embedding,
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "space_id": space_id,
                })

            return entities

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return []

    async def extract_relations(
        self,
        document_content: str,
        entities: list,
        llm,
    ) -> list[dict]:
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

Return a JSON object with a "relationships" array."""),
            ("user", """Entities:
{entity_list}

Document:
{document}

Extract relationships:""")
        ])

        try:
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
                    relations.append({
                        "source_entity_id": source_id,
                        "target_entity_id": target_id,
                        "relation_type": r["type"],
                        "description": r.get("description"),
                        "weight": r.get("weight", 1.0),
                        "space_id": entities[0].space_id,
                        "document_id": entities[0].document_id,
                    })

            return relations

        except Exception as e:
            logger.error(f"Relation extraction error: {e}")
            return []

    async def merge_similar_entities(
        self,
        entities: list[dict],
        similarity_threshold: float = 0.85,
    ) -> list[dict]:
        """合并相似实体（去重）"""
        # TODO: 使用 embedding 相似度计算
        # 1. 计算所有实体对之间的余弦相似度
        # 2. 将相似度 > threshold 的实体合并
        # 3. 合并时保留描述更详细的实体，合并别名

        # 简化实现：仅按名称去重
        seen = set()
        merged = []
        for e in entities:
            name_lower = e["name"].lower()
            if name_lower not in seen:
                seen.add(name_lower)
                merged.append(e)

        return merged

    async def generate_embedding(self, text: str) -> list[float]:
        """生成文本的向量嵌入"""
        # TODO: 使用与 Document/Chunk 相同的 embedding 服务
        from langflow.services.embeddings import get_embedding_service
        service = get_embedding_service()
        return await service.embed_query(text)
```

---

### Phase 3: 语义查询融合 (第 5-7.5 周)

#### 3.1 统一搜索 API

**新增文件**: `src/backend/base/langflow/api/v1/search.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from langflow.services.deps import get_session, get_current_active_user
from langflow.services.database.models.user.model import User
from langflow.services.database.models.entity.crud import EntityCRUD
from langflow.services.database.models.relation.crud import RelationCRUD

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/")
async def unified_search(
    query: str,
    space_id: int,
    mode: str = "hybrid",  # "document", "entity", "hybrid"
    top_k: int = 10,
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    统一搜索接口 - 同时搜索文档和实体

    Args:
        query: 搜索查询
        space_id: 空间ID
        mode: 搜索模式
        top_k: 返回结果数量
        filters: 额外过滤条件

    Returns:
        {
            "documents": [...],
            "entities": [...],
            "relations": [...],
        }
    """
    # 检查权限
    # TODO: 实现权限检查

    results = {"documents": [], "entities": [], "relations": []}

    # 1. 文档检索
    if mode in ["document", "hybrid"]:
        # TODO: 使用现有的文档混合检索
        # from langflow.services.retrieval import DocumentHybridSearchRetriever
        # documents = await DocumentHybridSearchRetriever.search(...)
        pass

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

        results["entities"] = [
            {
                "id": e.id,
                "name": e.name,
                "type": e.entity_type,
                "description": e.description,
            }
            for e in entities
        ]

        # 获取实体之间的关系
        entity_ids = [e.id for e in entities]
        relations = await RelationCRUD.get_relations_by_entities(
            session=session,
            entity_ids=entity_ids,
        )

        results["relations"] = [
            {
                "id": r.id,
                "source_id": r.source_entity_id,
                "target_id": r.target_entity_id,
                "type": r.relation_type,
                "description": r.description,
            }
            for r in relations
        ]

    return results
```

#### 3.2 实体 API

**新增文件**: `src/backend/base/langflow/api/v1/entities.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from langflow.services.deps import get_session, get_current_active_user
from langflow.services.database.models.user.model import User
from langflow.services.database.models.entity.crud import EntityCRUD
from langflow.services.database.models.relation.crud import RelationCRUD
from langflow.services.database.models.document.model import Document

router = APIRouter(prefix="/entities", tags=["entities"])

@router.get("/")
async def list_entities(
    space_id: int,
    entity_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """获取实体列表"""
    # TODO: 检查权限

    entities = await EntityCRUD.get_entities_by_space(
        session=session,
        space_id=space_id,
        entity_type=entity_type,
        page=page,
        page_size=page_size,
    )

    return {
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "type": e.entity_type,
                "description": e.description,
                "aliases": e.aliases,
            }
            for e in entities
        ],
        "page": page,
        "page_size": page_size,
    }

@router.get("/{entity_id}")
async def get_entity_details(
    entity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """获取实体详情（包含相关文档和关系）"""
    entity, relations = await EntityCRUD.get_entity_with_relations(
        session=session,
        entity_id=entity_id,
    )

    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # TODO: 检查权限

    # 获取相关文档
    related_docs = []
    if entity.document_id:
        doc = await session.get(Document, entity.document_id)
        if doc:
            related_docs.append({
                "id": doc.id,
                "title": doc.title,
            })

    return {
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "type": entity.entity_type,
            "description": entity.description,
            "aliases": entity.aliases,
        },
        "related_documents": related_docs,
        "relations": [
            {
                "id": r.id,
                "source_id": r.source_entity_id,
                "target_id": r.target_entity_id,
                "type": r.relation_type,
            }
            for r in relations
        ],
    }

@router.put("/{entity_id}")
async def update_entity(
    entity_id: int,
    name: str | None = None,
    description: str | None = None,
    aliases: list[str] | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """更新实体（人工校正）"""
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if aliases is not None:
        update_data["aliases"] = aliases

    entity = await EntityCRUD.update_entity(
        session=session,
        entity_id=entity_id,
        update_data=update_data,
    )

    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.entity_type,
        "description": entity.description,
    }

@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """删除实体"""
    await EntityCRUD.delete_entity(session=session, entity_id=entity_id)
    return {"message": "Entity deleted successfully"}
```

#### 3.3 图谱查询 API

**新增文件**: `src/backend/base/langflow/api/v1/graphs.py`

```python
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from langflow.services.deps import get_session, get_current_active_user
from langflow.services.database.models.user.model import User
from langflow.services.database.models.entity.crud import EntityCRUD
from langflow.services.database.models.relation.crud import RelationCRUD

router = APIRouter(prefix="/graphs", tags=["graphs"])

@router.get("/{space_id}/subgraph")
async def get_subgraph(
    space_id: int,
    entity_ids: list[int] | None = None,
    max_depth: int = 2,
    max_nodes: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取子图 (用于可视化)

    Args:
        space_id: 空间ID
        entity_ids: 起始实体ID列表
        max_depth: 最大遍历深度
        max_nodes: 最大节点数

    Returns:
        {
            "nodes": [...],
            "edges": [...],
        }
    """
    # TODO: 检查权限

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
        entities = await EntityCRUD.get_entities_by_space(
            session=session,
            space_id=space_id,
            page=1,
            page_size=max_nodes,
        )
        entity_ids = [e.id for e in entities]
        relations = await RelationCRUD.get_relations_by_entities(
            session=session,
            entity_ids=entity_ids,
        )
        subgraph = {"entities": entities, "relations": relations}

    return {
        "nodes": [
            {
                "id": e.id,
                "label": e.name,
                "type": e.entity_type,
            }
            for e in subgraph["entities"]
        ],
        "edges": [
            {
                "source": r.source_entity_id,
                "target": r.target_entity_id,
                "label": r.relation_type,
            }
            for r in subgraph["relations"]
        ],
    }

async def build_subgraph_from_entities(
    session: AsyncSession,
    entity_ids: list[int],
    max_depth: int,
    max_nodes: int,
) -> dict:
    """从给定实体扩展子图 (BFS遍历)"""
    visited_entities = set(entity_ids)
    visited_relations = set()
    entities = []
    relations = []

    # BFS 遍历
    queue = [(eid, 0) for eid in entity_ids]

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
```

---

## 四、时间和资源估算

### 4.1 详细工时分解 (仅后端)

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
| **Phase 4** | 测试和优化 | 80-100h | 1.5-2 周 |
| 4.1 | 单元测试 | 30-40h | 0.5 周 |
| 4.2 | 集成测试 | 30-40h | 0.5 周 |
| 4.3 | 性能优化 | 20-20h | 0.5 周 |
| **总计** | | **380-490h** | **7-9 周** |

### 4.2 里程碑

- **M1 (1.5周)**: 数据模型就绪，可创建实体/关系
- **M2 (4.5周)**: 知识构建管道完成，文档上传自动提取实体
- **M3 (7周)**: API 层完成，可通过 API 查询实体和图谱
- **M4 (9周)**: 测试通过，后端生产就绪

---

## 五、风险与缓解

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| LLM 提取质量不稳定 | 高 | 提供人工校正接口，允许用户编辑实体 |
| 实体去重算法效果差 | 中 | 使用 embedding 相似度 + 人工审核 |
| 图谱性能问题 | 中 | 限制遍历深度，使用分页，考虑 Neo4j |
| Neo4j 额外依赖 | 低 | 先用 PostgreSQL，Neo4j 作为可选优化 |
| pgvector 扩展缺失 | 中 | 提供安装文档，或使用纯 Python 实现 |

---

## 六、验收标准

### 6.1 功能验收

- [ ] ✅ 文档上传后自动提取实体和关系
- [ ] ✅ 可通过 API 查询实体列表和详情
- [ ] ✅ 可通过 API 获取图谱数据 (subgraph)
- [ ] ✅ 统一搜索可同时查询文档和实体
- [ ] ✅ 实体可链接到来源文档
- [ ] ✅ 支持图谱遍历 (BFS)
- [ ] ✅ 用户可手动编辑实体和关系

### 6.2 性能验收

- [ ] 1000文档的实体提取 < 10分钟 (并行处理)
- [ ] 实体检索响应时间 < 1秒
- [ ] 图谱遍历响应时间 < 2秒 (100节点)
- [ ] 统一搜索响应时间 < 2秒

### 6.3 质量验收

- [ ] 单元测试覆盖率 > 70%
- [ ] API 集成测试通过
- [ ] RBAC 权限正确实施
- [ ] API 文档完整

---

## 七、下一步行动

### 7.1 立即可做 (无需审批)

1. **创建数据库迁移文件**
   ```bash
   cd src/backend/base/langflow
   alembic revision -m "add_knowledge_graph_tables"
   ```

2. **创建目录结构**
   ```bash
   mkdir -p src/backend/base/langflow/services/database/models/entity
   mkdir -p src/backend/base/langflow/services/database/models/relation
   mkdir -p src/backend/base/langflow/services/knowledge
   ```

3. **实现 Entity/Relation 模型**
   - 创建 `model.py` 和 `crud.py`
   - 添加到 `__init__.py`

### 7.2 需要决策的问题

**Q1: Neo4j 是否必需？**
- 推荐：先用 PostgreSQL，性能不足再上 Neo4j
- 优势：减少依赖，开发更快
- 劣势：图遍历性能较差

**Q2: 实体提取策略？**
- 推荐：先用 LLM 提取
- 优势：质量高，开发简单
- 劣势：成本较高

**Q3: pgvector 使用？**
- 推荐：使用 pgvector 进行向量搜索
- 备选：纯 Python 计算余弦相似度

---

## 八、总结

**后端融合方案核心优势**：

✅ **真正融合**：图谱能力深度集成到 SurfSense 后端
✅ **用户无感知**：文档上传自动构建图谱
✅ **统一体验**：单一搜索 API 同时返回文档和实体
✅ **代码复用**：利用现有 Document/Chunk 处理管道
✅ **最小依赖**：先用 PostgreSQL，Neo4j 可选

**预期效果**: SurfSense 后端具备世界级的知识图谱能力，为未来的前端提供强大的 API 支持。

---

**文档生成时间**: 2026-01-04
**版本**: 1.0 (后端专注版)
