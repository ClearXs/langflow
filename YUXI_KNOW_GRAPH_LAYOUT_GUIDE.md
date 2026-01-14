# Yuxi-Know 知识图谱布局算法实现指南

> ReactFlow 布局算法详细实现（映射 G6 Force 布局）

**关联文档：**
- [完整迁移计划](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)
- [实施清单](./YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md)
- [实施指南](./YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md)

---

## 目录

1. [布局算法对比](#布局算法对比)
2. [Dagre 层次布局](#dagre-层次布局)
3. [D3 Force 力导向布局](#d3-force-力导向布局)
4. [增量布局](#增量布局)
5. [自定义节点组件](#自定义节点组件)
6. [自定义边组件](#自定义边组件)
7. [交互功能](#交互功能)

---

## 布局算法对比

### G6 vs ReactFlow 布局

| 特性 | G6 (Yuxi-Know) | ReactFlow (Langflow) |
|------|----------------|----------------------|
| **默认布局** | d3-force | 无（需手动实现） |
| **布局库** | 内置 | 需要外部库（dagre, d3-force） |
| **配置** | `layout: { type: 'd3-force', ... }` | 自定义函数计算 position |
| **动画** | 内置支持 | 使用 CSS transition |
| **增量布局** | 自动 | 需手动实现 |

### 迁移策略

1. **Dagre 布局** - 用于层次结构清晰的图谱
2. **D3 Force 布局** - 映射 G6 的力导向布局（保持视觉一致性）
3. **增量布局** - 扩展邻居时，仅对新节点布局

---

## Dagre 层次布局

### 安装依赖

```bash
cd src/frontend
npm install dagre @types/dagre
```

### 文件：`src/frontend/src/utils/graph/layout-dagre.ts`

```typescript
/**
 * Dagre 层次布局算法
 *
 * 用于树状或层次结构的知识图谱
 */

import dagre from 'dagre'
import type { GraphNode, GraphEdge } from '@/types/api/graphs'

export interface DagreLayoutOptions {
  direction: 'TB' | 'LR' | 'BT' | 'RL'  // Top-Bottom, Left-Right, etc.
  nodeWidth: number
  nodeHeight: number
  rankSep: number     // 层级间距
  nodeSep: number     // 节点间距
  marginX: number
  marginY: number
}

const DEFAULT_OPTIONS: DagreLayoutOptions = {
  direction: 'TB',
  nodeWidth: 150,
  nodeHeight: 80,
  rankSep: 100,
  nodeSep: 50,
  marginX: 50,
  marginY: 50,
}

/**
 * 应用 Dagre 布局
 */
export function applyDagreLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: Partial<DagreLayoutOptions> = {}
): GraphNode[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // 创建 dagre 图
  const dagreGraph = new dagre.graphlib.Graph()

  // 设置图配置
  dagreGraph.setGraph({
    rankdir: opts.direction,
    ranksep: opts.rankSep,
    nodesep: opts.nodeSep,
    marginx: opts.marginX,
    marginy: opts.marginY,
  })

  // 设置默认节点和边配置
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  // 添加节点到 dagre 图
  nodes.forEach(node => {
    // 根据 degree 动态调整节点大小
    const size = calculateNodeSize(node.data.degree)

    dagreGraph.setNode(node.id, {
      width: size,
      height: size,
    })
  })

  // 添加边到 dagre 图
  edges.forEach(edge => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  // 计算布局
  dagre.layout(dagreGraph)

  // 更新节点位置
  const layoutedNodes = nodes.map(node => {
    const nodeWithPosition = dagreGraph.node(node.id)

    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWithPosition.width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    }
  })

  return layoutedNodes
}

/**
 * 计算节点大小（映射 G6 的大小计算）
 */
function calculateNodeSize(degree: number): number {
  // 映射 G6: Math.min(15 + degree * 5, 50)
  const baseSize = 60  // ReactFlow 默认大小
  const sizeIncrement = degree * 10

  return Math.min(baseSize + sizeIncrement, 150)
}
```

---

## D3 Force 力导向布局

### 安装依赖

```bash
cd src/frontend
npm install d3-force d3-force-3d
```

### 文件：`src/frontend/src/utils/graph/layout-force.ts`

```typescript
/**
 * D3 Force 力导向布局
 *
 * 映射 G6 的 d3-force 配置，保持视觉一致性
 */

import {
  forceSimulation,
  forceLink,
  forceCollide,
  forceManyBody,
  forceCenter,
  forceX,
  forceY,
  SimulationNodeDatum,
  SimulationLinkDatum,
} from 'd3-force'

import type { GraphNode, GraphEdge } from '@/types/api/graphs'

export interface ForceLayoutOptions {
  width: number
  height: number
  iterations: number
  linkDistance: number
  linkStrength: number
  chargeStrength: number
  centerStrength: number
  preventOverlap: boolean
}

const DEFAULT_OPTIONS: ForceLayoutOptions = {
  width: 1200,
  height: 800,
  iterations: 150,          // 映射 G6: iterations: 150
  linkDistance: 100,        // 映射 G6: link.distance: 100
  linkStrength: 0.8,        // 映射 G6: link.strength: 0.8
  chargeStrength: -400,     // 映射 G6: charge.strength: -400
  centerStrength: 0.1,      // 映射 G6: center.strength: 0.1
  preventOverlap: true,     // 映射 G6: preventOverlap: true
}

interface ForceNode extends SimulationNodeDatum {
  id: string
  degree: number
  x?: number
  y?: number
}

interface ForceLink extends SimulationLinkDatum<ForceNode> {
  source: string | ForceNode
  target: string | ForceNode
}

/**
 * 应用 D3 Force 布局（映射 G6 配置）
 */
export function applyForceLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: Partial<ForceLayoutOptions> = {}
): GraphNode[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // 准备节点数据
  const forceNodes: ForceNode[] = nodes.map(node => ({
    id: node.id,
    degree: node.data.degree,
    x: node.position.x || opts.width / 2,
    y: node.position.y || opts.height / 2,
  }))

  // 准备边数据
  const forceLinks: ForceLink[] = edges.map(edge => ({
    source: edge.source,
    target: edge.target,
  }))

  // 创建力导向模拟
  const simulation = forceSimulation(forceNodes)
    // 连接力（映射 G6 link）
    .force('link', forceLink(forceLinks)
      .id((d: any) => d.id)
      .distance(opts.linkDistance)
      .strength(opts.linkStrength)
    )

    // 排斥力（映射 G6 charge）
    .force('charge', forceManyBody()
      .strength(opts.chargeStrength)
      .distanceMax(600)  // 映射 G6: charge.distanceMax: 600
    )

    // 中心力（映射 G6 center）
    .force('center', forceCenter(opts.width / 2, opts.height / 2)
      .strength(opts.centerStrength)
    )

    // X/Y 轴力（保持节点在画布内）
    .force('x', forceX(opts.width / 2).strength(0.05))
    .force('y', forceY(opts.height / 2).strength(0.05))

  // 碰撞力（映射 G6 preventOverlap）
  if (opts.preventOverlap) {
    simulation.force('collide', forceCollide()
      .radius((d: any) => calculateNodeRadius(d.degree) + 10)
      .strength(0.7)
    )
  }

  // 运行指定次数的迭代
  simulation.tick(opts.iterations)
  simulation.stop()

  // 更新节点位置
  const layoutedNodes = nodes.map((node, index) => {
    const forceNode = forceNodes[index]

    return {
      ...node,
      position: {
        x: forceNode.x || 0,
        y: forceNode.y || 0,
      },
    }
  })

  return layoutedNodes
}

/**
 * 计算节点半径（映射 G6 的大小计算）
 */
function calculateNodeRadius(degree: number): number {
  // 映射 G6: Math.min(15 + degree * 5, 50)
  const size = Math.min(15 + degree * 5, 50)
  return size / 2
}

/**
 * 动画版本的 Force 布局（使用 requestAnimationFrame）
 */
export function applyForceLayoutAnimated(
  nodes: GraphNode[],
  edges: GraphEdge[],
  onTick: (nodes: GraphNode[]) => void,
  options: Partial<ForceLayoutOptions> = {}
): () => void {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // 准备数据
  const forceNodes: ForceNode[] = nodes.map(node => ({
    id: node.id,
    degree: node.data.degree,
    x: node.position.x || opts.width / 2,
    y: node.position.y || opts.height / 2,
  }))

  const forceLinks: ForceLink[] = edges.map(edge => ({
    source: edge.source,
    target: edge.target,
  }))

  // 创建模拟
  const simulation = forceSimulation(forceNodes)
    .force('link', forceLink(forceLinks)
      .id((d: any) => d.id)
      .distance(opts.linkDistance)
      .strength(opts.linkStrength)
    )
    .force('charge', forceManyBody()
      .strength(opts.chargeStrength)
      .distanceMax(600)
    )
    .force('center', forceCenter(opts.width / 2, opts.height / 2)
      .strength(opts.centerStrength)
    )
    .force('x', forceX(opts.width / 2).strength(0.05))
    .force('y', forceY(opts.height / 2).strength(0.05))

  if (opts.preventOverlap) {
    simulation.force('collide', forceCollide()
      .radius((d: any) => calculateNodeRadius(d.degree) + 10)
      .strength(0.7)
    )
  }

  // 每次 tick 更新节点位置
  simulation.on('tick', () => {
    const layoutedNodes = nodes.map((node, index) => {
      const forceNode = forceNodes[index]

      return {
        ...node,
        position: {
          x: forceNode.x || 0,
          y: forceNode.y || 0,
        },
      }
    })

    onTick(layoutedNodes)
  })

  // 返回停止函数
  return () => {
    simulation.stop()
  }
}
```

---

## 增量布局

### 文件：`src/frontend/src/utils/graph/layout-incremental.ts`

```typescript
/**
 * 增量布局算法
 *
 * 用于扩展邻居时，仅对新节点进行布局
 */

import type { GraphNode, GraphEdge } from '@/types/api/graphs'
import { applyForceLayout } from './layout-force'

/**
 * 增量布局：在现有节点周围放置新节点
 */
export function applyIncrementalLayout(
  allNodes: GraphNode[],
  allEdges: GraphEdge[],
  existingNodes: GraphNode[],
  newNodes: GraphNode[],
  centerNode: GraphNode
): GraphNode[] {
  // 如果没有新节点，直接返回
  if (newNodes.length === 0) {
    return allNodes
  }

  // 计算中心节点周围的圆形位置
  const radius = 200  // 新节点距离中心节点的半径
  const angleStep = (2 * Math.PI) / newNodes.length

  // 初始化新节点的位置（圆形排列）
  const nodesWithInitialPosition = allNodes.map(node => {
    // 如果是已存在的节点，保持原位置
    const existingNode = existingNodes.find(n => n.id === node.id)
    if (existingNode) {
      return {
        ...node,
        position: existingNode.position,
      }
    }

    // 如果是新节点，放在中心节点周围
    const index = newNodes.findIndex(n => n.id === node.id)
    if (index !== -1) {
      const angle = index * angleStep
      return {
        ...node,
        position: {
          x: centerNode.position.x + radius * Math.cos(angle),
          y: centerNode.position.y + radius * Math.sin(angle),
        },
      }
    }

    return node
  })

  // 对所有节点运行短时间的 Force 布局（仅 50 次迭代）
  const layoutedNodes = applyForceLayout(
    nodesWithInitialPosition,
    allEdges,
    {
      iterations: 50,  // 短时间迭代，避免打乱已有布局
      linkStrength: 0.5,
      chargeStrength: -200,
    }
  )

  return layoutedNodes
}

/**
 * 固定节点位置的 Force 布局
 *
 * 允许指定某些节点固定不动
 */
export function applyForceLayoutWithFixed(
  nodes: GraphNode[],
  edges: GraphEdge[],
  fixedNodeIds: string[]
): GraphNode[] {
  // TODO: 实现固定节点的 Force 布局
  // 可以通过设置 fx, fy 属性来固定节点
  return nodes
}
```

---

## 自定义节点组件

### 文件：`src/frontend/src/components/graph/EntityNode.tsx`

```tsx
/**
 * 实体节点组件
 *
 * 映射 G6 的圆形节点样式
 *
 * 功能：
 * - 圆形节点
 * - 根据 degree 动态调整大小
 * - 10 种实体类型颜色
 * - Hover 高亮效果
 * - 拖拽支持
 */

import { memo, useCallback } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'
import { getEntityTypeColor } from '@/utils/graph/colors'
import type { GraphNode } from '@/types/api/graphs'

export const EntityNode = memo(({ data, selected }: NodeProps<GraphNode['data']>) => {
  const { label, entityType, degree } = data

  // 计算节点大小（映射 G6: Math.min(15 + degree * 5, 50)）
  const size = Math.min(60 + degree * 10, 150)
  const radius = size / 2

  // 获取实体类型颜色
  const color = getEntityTypeColor(entityType)

  return (
    <div
      className={cn(
        'relative flex items-center justify-center rounded-full transition-all duration-200',
        'border-2 cursor-pointer',
        selected ? 'ring-4 ring-blue-500 ring-opacity-50' : '',
      )}
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        borderColor: selected ? '#3b82f6' : 'white',
        boxShadow: selected
          ? '0 10px 25px rgba(0, 0, 0, 0.3)'
          : '0 4px 10px rgba(0, 0, 0, 0.2)',
      }}
    >
      {/* 节点 Handles（连接点） */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
      />

      {/* 节点标签 */}
      <div
        className="absolute text-center font-medium text-white"
        style={{
          fontSize: Math.max(12, size / 8),
          maxWidth: size * 0.8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </div>

      {/* Degree 徽章（显示连接数） */}
      {degree > 0 && (
        <div
          className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center"
          style={{
            width: 24,
            height: 24,
          }}
        >
          {degree}
        </div>
      )}
    </div>
  )
})

EntityNode.displayName = 'EntityNode'
```

---

## 自定义边组件

### 文件：`src/frontend/src/components/graph/RelationEdge.tsx`

```tsx
/**
 * 关系边组件
 *
 * 映射 G6 的 quadratic 边样式
 *
 * 功能：
 * - 贝塞尔曲线
 * - 箭头
 * - 边标签（关系类型）
 * - 根据 weight 调整样式
 */

import { memo } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  EdgeProps,
  getBezierPath,
  useReactFlow,
} from '@xyflow/react'
import { getEdgeOpacity, getEdgeWidth } from '@/utils/graph/colors'
import type { GraphEdge } from '@/types/api/graphs'

export const RelationEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: EdgeProps<GraphEdge['data']>) => {
  const { relationType, weight } = data

  // 计算贝塞尔曲线路径
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  // 根据权重计算样式
  const opacity = getEdgeOpacity(weight)
  const strokeWidth = getEdgeWidth(weight)

  return (
    <>
      {/* 边路径 */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: selected ? '#3b82f6' : '#9ca3af',
          strokeWidth: selected ? strokeWidth + 1 : strokeWidth,
          opacity: selected ? 1 : opacity,
        }}
      />

      {/* 边标签 */}
      <EdgeLabelRenderer>
        <div
          className="absolute text-xs font-medium bg-white px-2 py-1 rounded shadow-sm border border-gray-200 pointer-events-none"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            opacity: selected ? 1 : 0.7,
          }}
        >
          {relationType}
        </div>
      </EdgeLabelRenderer>
    </>
  )
})

RelationEdge.displayName = 'RelationEdge'
```

---

## 交互功能

### 文件：`src/frontend/src/components/graph/GraphCanvas.tsx`

```tsx
/**
 * 图谱画布组件
 *
 * 集成 ReactFlow 和所有交互功能
 */

import { useCallback, useEffect, useMemo } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { EntityNode } from './EntityNode'
import { RelationEdge } from './RelationEdge'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphNode, GraphEdge } from '@/types/api/graphs'

// 注册自定义节点和边类型
const nodeTypes = {
  entityNode: EntityNode,
}

const edgeTypes = {
  relationEdge: RelationEdge,
}

interface GraphCanvasProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (node: GraphNode) => void
  onEdgeClick?: (edge: GraphEdge) => void
}

export function GraphCanvas({
  nodes: initialNodes,
  edges: initialEdges,
  onNodeClick,
  onEdgeClick,
}: GraphCanvasProps) {
  const { selectNode, selectEdge, updateNode } = useGraphStore()

  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<GraphEdge>(initialEdges)

  // 同步外部节点和边的变化
  useEffect(() => {
    setNodes(initialNodes)
  }, [initialNodes, setNodes])

  useEffect(() => {
    setEdges(initialEdges)
  }, [initialEdges, setEdges])

  // 节点点击事件
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const graphNode = node as GraphNode
      selectNode(graphNode)
      onNodeClick?.(graphNode)
    },
    [selectNode, onNodeClick]
  )

  // 边点击事件
  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const graphEdge = edge as GraphEdge
      selectEdge(graphEdge)
      onEdgeClick?.(graphEdge)
    },
    [selectEdge, onEdgeClick]
  )

  // 画布点击事件（取消选中）
  const handlePaneClick = useCallback(() => {
    selectNode(null)
    selectEdge(null)
  }, [selectNode, selectEdge])

  // 节点拖拽结束事件（保存新位置）
  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      updateNode(node.id, { position: node.position })
    },
    [updateNode]
  )

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        onNodeDragStop={handleNodeDragStop}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        minZoom={0.1}
        maxZoom={4}
        defaultEdgeOptions={{
          type: 'relationEdge',
          animated: false,
        }}
      >
        {/* 控制面板 */}
        <Controls
          showZoom
          showFitView
          showInteractive
          position="bottom-right"
        />

        {/* 背景网格 */}
        <Background
          color="#e5e7eb"
          gap={16}
          size={1}
        />

        {/* 小地图 */}
        <MiniMap
          nodeColor={(node) => {
            const graphNode = node as GraphNode
            return getEntityTypeColor(graphNode.data.entityType)
          }}
          position="bottom-left"
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  )
}
```

---

## 使用示例

### 在页面中使用

```tsx
// src/frontend/src/pages/SpaceDetailPage/GraphPage.tsx

import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { GraphCanvas } from '@/components/graph/GraphCanvas'
import { useGetEntitiesQuery, useGetSubgraphQuery } from '@/controllers/API/queries/graphs'
import { transformEntitiesToNodes, transformRelationsToEdges } from '@/utils/graph'
import { applyForceLayout } from '@/utils/graph/layout-force'

export default function GraphPage() {
  const { spaceId } = useParams()

  // Step 1: 获取前 20 个实体
  const { data: entitiesData } = useGetEntitiesQuery({
    space_id: Number(spaceId),
    page_size: 20,
  })

  // Step 2: 使用前 10 个实体 ID 获取子图
  const startingIds = useMemo(
    () => entitiesData?.items.slice(0, 10).map(e => e.id) || [],
    [entitiesData]
  )

  const { data: subgraphData, isLoading } = useGetSubgraphQuery(
    Number(spaceId),
    { entity_ids: startingIds, max_depth: 2, max_nodes: 100 },
    { enabled: startingIds.length > 0 }
  )

  // Step 3: 转换数据并应用布局
  const { nodes, edges } = useMemo(() => {
    if (!subgraphData) return { nodes: [], edges: [] }

    const transformedNodes = transformEntitiesToNodes(
      subgraphData.entities,
      subgraphData.relations
    )
    const transformedEdges = transformRelationsToEdges(subgraphData.relations)

    // 应用 Force 布局
    const layoutedNodes = applyForceLayout(transformedNodes, transformedEdges, {
      width: window.innerWidth,
      height: window.innerHeight - 200,
    })

    return { nodes: layoutedNodes, edges: transformedEdges }
  }, [subgraphData])

  if (isLoading) {
    return <div>Loading graph...</div>
  }

  return (
    <div className="h-full">
      <GraphCanvas nodes={nodes} edges={edges} />
    </div>
  )
}
```

---

**文档版本：** 1.0
**更新日期：** 2026-01-09
**状态：** 📋 布局算法实现完成
