# Yuxi-Know 知识图谱前端实施指南

> 详细的代码实现指南和最佳实践

**关联文档：**
- [完整迁移计划](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)
- [实施清单](./YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md)

---

## 目录

1. [项目结构](#项目结构)
2. [类型定义完整实现](#类型定义完整实现)
3. [React Query Hooks 完整实现](#react-query-hooks-完整实现)
4. [Zustand Store 完整实现](#zustand-store-完整实现)
5. [数据转换工具](#数据转换工具)
6. [布局算法实现](#布局算法实现)
7. [自定义节点组件](#自定义节点组件)
8. [自定义边组件](#自定义边组件)
9. [主画布组件](#主画布组件)
10. [页面组件](#页面组件)

---

## 项目结构

### 完整目录树

```
src/frontend/src/
├── types/
│   └── api/
│       └── graphs.ts                          # Graph API 类型定义
├── controllers/
│   └── API/
│       └── queries/
│           └── graphs/
│               ├── index.ts                   # 导出所有 hooks
│               ├── use-get-entities.ts        # 获取实体列表
│               ├── use-get-subgraph.ts        # 获取子图
│               ├── use-expand-neighbors.ts    # 扩展邻居
│               └── use-get-graph-stats.ts     # 获取统计
├── stores/
│   └── graphStore.ts                          # Graph 状态管理
├── utils/
│   └── graph/
│       ├── index.ts                           # 导出所有工具
│       ├── transform-entities.ts              # 实体转节点
│       ├── transform-relations.ts             # 关系转边
│       ├── layout-dagre.ts                    # Dagre 布局
│       ├── layout-force.ts                    # Force 布局
│       └── colors.ts                          # 颜色映射
├── components/
│   └── graph/
│       ├── GraphCanvas.tsx                    # 主画布
│       ├── EntityNode.tsx                     # 实体节点
│       ├── RelationEdge.tsx                   # 关系边
│       ├── GraphToolbar.tsx                   # 工具栏
│       ├── GraphSearchBar.tsx                 # 搜索栏
│       ├── GraphFilters.tsx                   # 过滤器
│       ├── GraphDetailPanel.tsx               # 详情面板
│       ├── GraphStats.tsx                     # 统计面板
│       ├── node-types.ts                      # 节点类型注册
│       └── index.ts                           # 导出所有组件
└── pages/
    └── SpaceDetailPage/
        └── GraphPage.tsx                      # Graph 页面

```

---

## 类型定义完整实现

### 文件：`src/frontend/src/types/api/graphs.ts`

```typescript
/**
 * Graph API Types
 *
 * 对应后端模型：
 * - Entity: src/backend/base/langflow/services/database/models/entity/model.py
 * - Relation: src/backend/base/langflow/services/database/models/relation/model.py
 */

// ==================== 基础实体类型 ====================

/**
 * 实体读取类型
 * 对应后端：EntityRead schema
 */
export interface EntityRead {
  id: number
  space_id: number
  document_id: number | null
  chunk_id: number | null
  name: string
  entity_type: string
  description: string | null
  aliases: string[]
  embedding: number[] | null
  properties: Record<string, any>
  created_at: string  // ISO datetime
  updated_at: string | null
}

/**
 * 实体创建类型
 * 对应后端：EntityCreate schema
 */
export interface EntityCreate {
  space_id: number
  document_id?: number | null
  chunk_id?: number | null
  name: string
  entity_type: string
  description?: string | null
  aliases?: string[]
  embedding?: number[] | null
  properties?: Record<string, any>
}

/**
 * 实体更新类型
 * 对应后端：EntityUpdate schema
 */
export interface EntityUpdate {
  name?: string
  entity_type?: string
  description?: string | null
  aliases?: string[]
  embedding?: number[] | null
  properties?: Record<string, any>
}

// ==================== 关系类型 ====================

/**
 * 关系读取类型
 * 对应后端：RelationRead schema
 */
export interface RelationRead {
  id: number
  space_id: number
  source_entity_id: number
  target_entity_id: number
  document_id: number | null
  chunk_id: number | null
  relation_type: string
  description: string | null
  weight: number  // 0.0 - 1.0
  properties: Record<string, any>
  created_at: string
  updated_at: string | null
}

/**
 * 关系创建类型
 */
export interface RelationCreate {
  space_id: number
  source_entity_id: number
  target_entity_id: number
  document_id?: number | null
  chunk_id?: number | null
  relation_type: string
  description?: string | null
  weight?: number
  properties?: Record<string, any>
}

// ==================== 图谱查询类型 ====================

/**
 * 子图请求类型
 * 对应后端：SubgraphRequest
 */
export interface SubgraphRequest {
  entity_ids: number[]      // 起始实体 ID 列表（必需）
  max_depth?: number        // 默认 2
  max_nodes?: number        // 默认 100
}

/**
 * 子图响应类型
 * 对应后端：SubgraphResponse
 */
export interface SubgraphResponse {
  entities: EntityRead[]
  relations: RelationRead[]
}

/**
 * 获取实体列表请求参数
 */
export interface GetEntitiesParams {
  space_id: number
  entity_type?: string      // 过滤实体类型
  search?: string           // 搜索名称（部分匹配）
  page?: number             // 默认 1
  page_size?: number        // 默认 50
}

/**
 * 分页响应类型
 */
export interface PaginatedResponse<T> {
  items: T[]
  page: number
  page_size: number
  total_count: number
}

/**
 * 扩展邻居请求
 */
export interface ExpandNeighborsRequest {
  space_id: number
  entity_id: number
  direction?: 'outgoing' | 'incoming' | 'both'  // 默认 'both'
}

/**
 * 扩展邻居响应
 */
export interface ExpandNeighborsResponse {
  entity_id: number
  relations: RelationRead[]
}

/**
 * 图谱统计响应
 * 对应后端：GET /graphs/{space_id}/stats
 */
export interface GraphStatsResponse {
  space_id: number
  entity_count: number
  relation_count: number
  entity_type_distribution: Record<string, number>
  relation_type_distribution: Record<string, number>
}

// ==================== ReactFlow 类型 ====================

import type { Node, Edge } from '@xyflow/react'

/**
 * 图谱节点类型（ReactFlow Node + 自定义数据）
 */
export interface GraphNode extends Node {
  type: 'entityNode'
  data: {
    label: string
    entityType: string
    description?: string | null
    degree: number          // 节点度数
    properties: Record<string, any>
    original: EntityRead    // 原始实体数据
  }
}

/**
 * 图谱边类型（ReactFlow Edge + 自定义数据）
 */
export interface GraphEdge extends Edge {
  type: 'relationEdge'
  label?: string
  animated?: boolean
  data: {
    relationType: string
    weight: number
    description?: string | null
    properties: Record<string, any>
    original: RelationRead  // 原始关系数据
  }
}

// ==================== 布局类型 ====================

/**
 * 布局类型
 */
export type LayoutType = 'dagre' | 'force'

/**
 * 布局选项
 */
export interface LayoutOptions {
  type: LayoutType
  direction?: 'TB' | 'LR' | 'BT' | 'RL'  // Dagre 方向
  nodeSpacing?: number                    // 节点间距
  rankSpacing?: number                    // 层级间距
  animate?: boolean                       // 动画过渡
}

/**
 * Force 布局配置（映射 G6 Force 配置）
 */
export interface ForceLayoutConfig {
  center?: { x: number; y: number }
  iterations?: number
  preventOverlap?: boolean
  nodeSize?: number
  linkDistance?: number
  linkStrength?: number
  chargeStrength?: number
}

// ==================== 过滤和搜索类型 ====================

/**
 * 图谱过滤器
 */
export interface GraphFilters {
  entityTypes: string[]     // 选中的实体类型
  relationTypes: string[]   // 选中的关系类型
  minWeight?: number        // 最小权重
  maxWeight?: number        // 最大权重
  searchQuery?: string      // 搜索关键词
}

/**
 * 高亮节点选项
 */
export interface HighlightOptions {
  nodeIds: string[]         // 要高亮的节点 ID
  fadedOpacity?: number     // 淡化节点的透明度（默认 0.3）
}

// ==================== 导出所有类型 ====================

export type {
  // 实体
  EntityRead,
  EntityCreate,
  EntityUpdate,

  // 关系
  RelationRead,
  RelationCreate,

  // 图谱查询
  SubgraphRequest,
  SubgraphResponse,
  GetEntitiesParams,
  PaginatedResponse,
  ExpandNeighborsRequest,
  ExpandNeighborsResponse,
  GraphStatsResponse,

  // ReactFlow
  GraphNode,
  GraphEdge,

  // 布局
  LayoutType,
  LayoutOptions,
  ForceLayoutConfig,

  // 过滤
  GraphFilters,
  HighlightOptions,
}
```

---

## React Query Hooks 完整实现

### 文件：`src/frontend/src/controllers/API/queries/graphs/use-get-entities.ts`

```typescript
/**
 * Hook: useGetEntitiesQuery
 *
 * 获取实体列表（支持分页、过滤、搜索）
 *
 * 后端端点：GET /api/v1/entities/
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import type { EntityRead, GetEntitiesParams, PaginatedResponse } from '@/types/api/graphs'

export function useGetEntitiesQuery(params: GetEntitiesParams) {
  return useQuery({
    queryKey: ['entities', params],

    queryFn: async () => {
      const response = await api.get<PaginatedResponse<EntityRead>>('/api/v1/entities/', {
        params: {
          space_id: params.space_id,
          entity_type: params.entity_type,
          search: params.search,
          page: params.page || 1,
          page_size: params.page_size || 50,
        }
      })

      return response.data
    },

    // 仅在 space_id 存在时启用
    enabled: !!params.space_id,

    // 缓存 30 秒
    staleTime: 30000,

    // 失败后重试 1 次
    retry: 1,

    // 后台自动刷新
    refetchOnWindowFocus: true,
  })
}

/**
 * Hook: useGetEntityByIdQuery
 *
 * 获取单个实体详情
 *
 * 后端端点：GET /api/v1/entities/{entity_id}
 */
export function useGetEntityByIdQuery(entityId: number | null) {
  return useQuery({
    queryKey: ['entity', entityId],

    queryFn: async () => {
      if (!entityId) throw new Error('Entity ID is required')

      const response = await api.get<EntityRead>(`/api/v1/entities/${entityId}`)
      return response.data
    },

    enabled: !!entityId,
    staleTime: 60000,  // 1 分钟缓存
  })
}
```

---

### 文件：`src/frontend/src/controllers/API/queries/graphs/use-get-subgraph.ts`

```typescript
/**
 * Hook: useGetSubgraphQuery
 *
 * 获取子图数据（BFS 遍历）
 *
 * 后端端点：POST /api/v1/graphs/{space_id}/subgraph
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import type { SubgraphRequest, SubgraphResponse } from '@/types/api/graphs'

export function useGetSubgraphQuery(
  spaceId: number | null,
  request: SubgraphRequest,
  options?: {
    enabled?: boolean
    staleTime?: number
  }
) {
  return useQuery({
    queryKey: ['subgraph', spaceId, request],

    queryFn: async () => {
      if (!spaceId) throw new Error('Space ID is required')
      if (!request.entity_ids.length) throw new Error('At least one entity ID is required')

      const response = await api.post<SubgraphResponse>(
        `/api/v1/graphs/${spaceId}/subgraph`,
        {
          entity_ids: request.entity_ids,
          max_depth: request.max_depth || 2,
          max_nodes: request.max_nodes || 100,
        }
      )

      return response.data
    },

    // 仅在 spaceId 存在且有 entity_ids 时启用
    enabled: (options?.enabled !== false) && !!spaceId && request.entity_ids.length > 0,

    // 缓存 1 分钟
    staleTime: options?.staleTime || 60000,

    // 子图数据较重要，失败后重试 2 次
    retry: 2,

    // 不在后台自动刷新（避免不必要的请求）
    refetchOnWindowFocus: false,
  })
}
```

---

### 文件：`src/frontend/src/controllers/API/queries/graphs/use-expand-neighbors.ts`

```typescript
/**
 * Hook: useExpandNeighbors
 *
 * 扩展邻居节点（Mutation）
 *
 * 流程：
 * 1. 获取实体的关系
 * 2. 提取新实体 ID
 * 3. 获取新实体详情
 * 4. 返回新节点和边
 *
 * 后端端点：GET /api/v1/graphs/{space_id}/entity/{entity_id}/relations
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import type {
  ExpandNeighborsRequest,
  ExpandNeighborsResponse,
  EntityRead,
  RelationRead
} from '@/types/api/graphs'

interface ExpandNeighborsResult {
  newEntities: EntityRead[]
  newRelations: RelationRead[]
}

export function useExpandNeighbors() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: ExpandNeighborsRequest): Promise<ExpandNeighborsResult> => {
      // Step 1: 获取实体的所有关系
      const relationsResponse = await api.get<ExpandNeighborsResponse>(
        `/api/v1/graphs/${request.space_id}/entity/${request.entity_id}/relations`,
        {
          params: {
            direction: request.direction || 'both'
          }
        }
      )

      const relations = relationsResponse.data.relations

      // Step 2: 提取新实体 ID（去重）
      const newEntityIds = new Set<number>()
      relations.forEach(rel => {
        if (rel.source_entity_id !== request.entity_id) {
          newEntityIds.add(rel.source_entity_id)
        }
        if (rel.target_entity_id !== request.entity_id) {
          newEntityIds.add(rel.target_entity_id)
        }
      })

      // Step 3: 并行获取所有新实体的详情
      const entityPromises = Array.from(newEntityIds).map(id =>
        api.get<EntityRead>(`/api/v1/entities/${id}`)
      )

      const entityResponses = await Promise.all(entityPromises)
      const newEntities = entityResponses.map(res => res.data)

      return {
        newEntities,
        newRelations: relations,
      }
    },

    onSuccess: (data, variables) => {
      // 使子图缓存失效，触发重新加载
      queryClient.invalidateQueries({
        queryKey: ['subgraph', variables.space_id]
      })

      // 也可以直接更新缓存（性能更好）
      // queryClient.setQueryData(['subgraph', variables.space_id], (old) => {
      //   if (!old) return old
      //   return {
      //     entities: [...old.entities, ...data.newEntities],
      //     relations: [...old.relations, ...data.newRelations],
      //   }
      // })
    },

    onError: (error) => {
      console.error('Failed to expand neighbors:', error)
    },
  })
}
```

---

### 文件：`src/frontend/src/controllers/API/queries/graphs/use-get-graph-stats.ts`

```typescript
/**
 * Hook: useGetGraphStatsQuery
 *
 * 获取图谱统计信息
 *
 * 后端端点：GET /api/v1/graphs/{space_id}/stats
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import type { GraphStatsResponse } from '@/types/api/graphs'

export function useGetGraphStatsQuery(spaceId: number | null) {
  return useQuery({
    queryKey: ['graph-stats', spaceId],

    queryFn: async () => {
      if (!spaceId) throw new Error('Space ID is required')

      const response = await api.get<GraphStatsResponse>(
        `/api/v1/graphs/${spaceId}/stats`
      )

      return response.data
    },

    enabled: !!spaceId,

    // 统计数据不常变，缓存 2 分钟
    staleTime: 120000,

    // 后台自动刷新
    refetchOnWindowFocus: true,
  })
}
```

---

### 文件：`src/frontend/src/controllers/API/queries/graphs/index.ts`

```typescript
/**
 * Graph Query Hooks
 *
 * 导出所有 graph 相关的 React Query hooks
 */

export { useGetEntitiesQuery, useGetEntityByIdQuery } from './use-get-entities'
export { useGetSubgraphQuery } from './use-get-subgraph'
export { useExpandNeighbors } from './use-expand-neighbors'
export { useGetGraphStatsQuery } from './use-get-graph-stats'
```

---

## Zustand Store 完整实现

### 文件：`src/frontend/src/stores/graphStore.ts`

```typescript
/**
 * Graph Store
 *
 * 使用 Zustand 管理知识图谱状态
 *
 * 功能：
 * - 管理节点和边
 * - 选中状态
 * - 过滤器
 * - 布局配置
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Node, Edge } from '@xyflow/react'
import type { GraphNode, GraphEdge, LayoutType, GraphFilters } from '@/types/api/graphs'

interface GraphState {
  // ========== 核心数据 ==========
  nodes: GraphNode[]
  edges: GraphEdge[]

  // ========== 选中状态 ==========
  selectedNode: GraphNode | null
  selectedEdge: GraphEdge | null
  selectedEntityIds: number[]  // 用于子图查询

  // ========== UI 状态 ==========
  showDetailPanel: boolean
  showStatsPanel: boolean

  // ========== 布局配置 ==========
  layoutType: LayoutType

  // ========== 过滤器 ==========
  filters: GraphFilters

  // ========== 高亮状态 ==========
  highlightedNodeIds: Set<string>

  // ========== Actions ==========

  // 设置节点和边
  setNodes: (nodes: GraphNode[]) => void
  setEdges: (edges: GraphEdge[]) => void

  // 添加节点和边（用于增量更新）
  addNodes: (nodes: GraphNode[]) => void
  addEdges: (edges: GraphEdge[]) => void

  // 更新节点（用于拖拽后位置更新）
  updateNode: (nodeId: string, updates: Partial<GraphNode>) => void

  // 删除节点和边
  removeNode: (nodeId: string) => void
  removeEdge: (edgeId: string) => void

  // 选中状态
  selectNode: (node: GraphNode | null) => void
  selectEdge: (edge: GraphEdge | null) => void
  setSelectedEntityIds: (ids: number[]) => void

  // UI 状态
  toggleDetailPanel: () => void
  toggleStatsPanel: () => void

  // 布局
  setLayoutType: (type: LayoutType) => void

  // 过滤器
  setFilters: (filters: Partial<GraphFilters>) => void
  resetFilters: () => void

  // 高亮
  highlightNodes: (nodeIds: string[]) => void
  clearHighlight: () => void

  // 重置所有状态
  reset: () => void
}

const initialFilters: GraphFilters = {
  entityTypes: [],
  relationTypes: [],
  minWeight: 0,
  maxWeight: 1,
  searchQuery: '',
}

export const useGraphStore = create<GraphState>()(
  devtools(
    (set, get) => ({
      // ========== 初始状态 ==========
      nodes: [],
      edges: [],
      selectedNode: null,
      selectedEdge: null,
      selectedEntityIds: [],
      showDetailPanel: false,
      showStatsPanel: true,
      layoutType: 'force',
      filters: initialFilters,
      highlightedNodeIds: new Set(),

      // ========== Actions 实现 ==========

      setNodes: (nodes) => set({ nodes }),

      setEdges: (edges) => set({ edges }),

      addNodes: (newNodes) => set((state) => {
        const existingIds = new Set(state.nodes.map(n => n.id))
        const uniqueNewNodes = newNodes.filter(n => !existingIds.has(n.id))
        return { nodes: [...state.nodes, ...uniqueNewNodes] }
      }),

      addEdges: (newEdges) => set((state) => {
        const existingIds = new Set(state.edges.map(e => e.id))
        const uniqueNewEdges = newEdges.filter(e => !existingIds.has(e.id))
        return { edges: [...state.edges, ...uniqueNewEdges] }
      }),

      updateNode: (nodeId, updates) => set((state) => ({
        nodes: state.nodes.map(node =>
          node.id === nodeId ? { ...node, ...updates } : node
        )
      })),

      removeNode: (nodeId) => set((state) => ({
        nodes: state.nodes.filter(n => n.id !== nodeId),
        edges: state.edges.filter(e =>
          e.source !== nodeId && e.target !== nodeId
        ),
        selectedNode: state.selectedNode?.id === nodeId ? null : state.selectedNode,
      })),

      removeEdge: (edgeId) => set((state) => ({
        edges: state.edges.filter(e => e.id !== edgeId),
        selectedEdge: state.selectedEdge?.id === edgeId ? null : state.selectedEdge,
      })),

      selectNode: (node) => set({
        selectedNode: node,
        selectedEdge: null,
        showDetailPanel: !!node,
      }),

      selectEdge: (edge) => set({
        selectedEdge: edge,
        selectedNode: null,
      }),

      setSelectedEntityIds: (ids) => set({ selectedEntityIds: ids }),

      toggleDetailPanel: () => set((state) => ({
        showDetailPanel: !state.showDetailPanel
      })),

      toggleStatsPanel: () => set((state) => ({
        showStatsPanel: !state.showStatsPanel
      })),

      setLayoutType: (type) => set({ layoutType: type }),

      setFilters: (newFilters) => set((state) => ({
        filters: { ...state.filters, ...newFilters }
      })),

      resetFilters: () => set({ filters: initialFilters }),

      highlightNodes: (nodeIds) => set({
        highlightedNodeIds: new Set(nodeIds)
      }),

      clearHighlight: () => set({
        highlightedNodeIds: new Set()
      }),

      reset: () => set({
        nodes: [],
        edges: [],
        selectedNode: null,
        selectedEdge: null,
        selectedEntityIds: [],
        showDetailPanel: false,
        showStatsPanel: true,
        layoutType: 'force',
        filters: initialFilters,
        highlightedNodeIds: new Set(),
      }),
    }),
    { name: 'GraphStore' }
  )
)
```

---

## 数据转换工具

### 文件：`src/frontend/src/utils/graph/transform-entities.ts`

```typescript
/**
 * 实体 → ReactFlow 节点转换
 *
 * 将后端 EntityRead 转换为 ReactFlow Node 格式
 */

import type { EntityRead, GraphNode, RelationRead } from '@/types/api/graphs'

/**
 * 计算实体的度数（连接的边数量）
 */
export function calculateDegree(
  entityId: number,
  relations: RelationRead[]
): number {
  return relations.filter(
    rel => rel.source_entity_id === entityId || rel.target_entity_id === entityId
  ).length
}

/**
 * 转换单个实体为节点
 */
export function transformEntityToNode(
  entity: EntityRead,
  degree: number = 0,
  position?: { x: number; y: number }
): GraphNode {
  return {
    id: String(entity.id),
    type: 'entityNode',
    position: position || { x: 0, y: 0 },  // 默认位置，待布局算法计算
    data: {
      label: entity.name,
      entityType: entity.entity_type,
      description: entity.description,
      degree,
      properties: entity.properties,
      original: entity,
    },
  }
}

/**
 * 批量转换实体为节点
 */
export function transformEntitiesToNodes(
  entities: EntityRead[],
  relations: RelationRead[] = []
): GraphNode[] {
  return entities.map(entity => {
    const degree = calculateDegree(entity.id, relations)
    return transformEntityToNode(entity, degree)
  })
}

/**
 * 根据搜索关键词过滤节点
 */
export function filterNodesBySearch(
  nodes: GraphNode[],
  searchQuery: string
): GraphNode[] {
  if (!searchQuery.trim()) return nodes

  const query = searchQuery.toLowerCase()

  return nodes.filter(node => {
    // 搜索名称
    if (node.data.label.toLowerCase().includes(query)) return true

    // 搜索别名
    const aliases = node.data.original.aliases || []
    if (aliases.some(alias => alias.toLowerCase().includes(query))) return true

    // 搜索描述
    if (node.data.description?.toLowerCase().includes(query)) return true

    return false
  })
}
```

---

### 文件：`src/frontend/src/utils/graph/transform-relations.ts`

```typescript
/**
 * 关系 → ReactFlow 边转换
 *
 * 将后端 RelationRead 转换为 ReactFlow Edge 格式
 */

import type { RelationRead, GraphEdge } from '@/types/api/graphs'

/**
 * 转换单个关系为边
 */
export function transformRelationToEdge(relation: RelationRead): GraphEdge {
  return {
    id: `e-${relation.id}`,
    source: String(relation.source_entity_id),
    target: String(relation.target_entity_id),
    type: 'relationEdge',
    label: relation.relation_type,

    // 高权重关系显示动画
    animated: relation.weight > 0.8,

    data: {
      relationType: relation.relation_type,
      weight: relation.weight,
      description: relation.description,
      properties: relation.properties,
      original: relation,
    },
  }
}

/**
 * 批量转换关系为边
 */
export function transformRelationsToEdges(relations: RelationRead[]): GraphEdge[] {
  return relations.map(transformRelationToEdge)
}

/**
 * 根据权重过滤边
 */
export function filterEdgesByWeight(
  edges: GraphEdge[],
  minWeight: number = 0,
  maxWeight: number = 1
): GraphEdge[] {
  return edges.filter(edge => {
    const weight = edge.data.weight
    return weight >= minWeight && weight <= maxWeight
  })
}

/**
 * 根据关系类型过滤边
 */
export function filterEdgesByType(
  edges: GraphEdge[],
  relationTypes: string[]
): GraphEdge[] {
  if (relationTypes.length === 0) return edges

  return edges.filter(edge =>
    relationTypes.includes(edge.data.relationType)
  )
}
```

---

### 文件：`src/frontend/src/utils/graph/colors.ts`

```typescript
/**
 * 颜色映射
 *
 * 映射 Yuxi-Know G6 的 colorMap（10 种颜色）
 */

/**
 * 实体类型颜色映射（G6 compatible）
 */
export const ENTITY_TYPE_COLORS: Record<string, string> = {
  // 默认 10 种颜色（映射 G6 colorMap）
  Person: '#5B8FF9',         // 蓝色
  Organization: '#5AD8A6',   // 绿色
  Location: '#5D7092',       // 灰蓝色
  Event: '#F6BD16',          // 黄色
  Product: '#E86452',        // 红色
  Concept: '#6DC8EC',        // 青色
  Technology: '#945FB9',     // 紫色
  Document: '#FF9845',       // 橙色
  Time: '#1E9493',           // 深青色
  Other: '#FF99C3',          // 粉色
}

/**
 * 获取实体类型对应的颜色
 */
export function getEntityTypeColor(entityType: string): string {
  return ENTITY_TYPE_COLORS[entityType] || ENTITY_TYPE_COLORS.Other
}

/**
 * 生成所有唯一实体类型的颜色映射
 */
export function generateColorMap(entityTypes: string[]): Record<string, string> {
  const uniqueTypes = Array.from(new Set(entityTypes))
  const colorMap: Record<string, string> = {}

  const defaultColors = Object.values(ENTITY_TYPE_COLORS)

  uniqueTypes.forEach((type, index) => {
    colorMap[type] = defaultColors[index % defaultColors.length]
  })

  return colorMap
}

/**
 * 根据权重计算边的透明度
 */
export function getEdgeOpacity(weight: number): number {
  // 权重 0.0-1.0 映射到透明度 0.3-1.0
  return 0.3 + (weight * 0.7)
}

/**
 * 根据权重计算边的粗细
 */
export function getEdgeWidth(weight: number): number {
  // 权重 0.0-1.0 映射到宽度 1-4
  return 1 + (weight * 3)
}
```

这个文档已经创建完成！我将继续创建布局算法和组件实现部分。要继续吗？