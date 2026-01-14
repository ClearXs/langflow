# Yuxi-Know 知识图谱迁移 - 快速参考卡

> 开发过程中的速查手册

---

## 🔥 最关键信息

### API 两步加载流程

```typescript
// ❌ 错误：Yuxi-Know 方式（Langflow 不支持）
GET /api/graph/subgraph?node_label=*

// ✅ 正确：Langflow 方式
// Step 1: 获取实体列表
const entities = await api.get('/entities/?space_id=123&page_size=20')

// Step 2: 使用实体 ID 获取子图
const subgraph = await api.post('/graphs/123/subgraph', {
  entity_ids: entities.items.slice(0, 10).map(e => e.id),
  max_depth: 2,
  max_nodes: 100
})
```

---

## 📁 核心文件路径

```bash
# 类型定义
src/frontend/src/types/api/graphs.ts

# API Hooks
src/frontend/src/controllers/API/queries/graphs/
├── use-get-entities.ts        # 获取实体列表
├── use-get-subgraph.ts         # 获取子图（BFS）
├── use-expand-neighbors.ts     # 扩展邻居
└── use-get-graph-stats.ts      # 统计信息

# 状态管理
src/frontend/src/stores/graphStore.ts

# 数据转换
src/frontend/src/utils/graph/
├── transform-entities.ts       # Entity → Node
├── transform-relations.ts      # Relation → Edge
├── colors.ts                   # 颜色映射

# 布局算法
src/frontend/src/utils/graph/
├── layout-dagre.ts             # 层次布局
├── layout-force.ts             # 力导向（G6 风格）
└── layout-incremental.ts       # 增量布局

# UI 组件
src/frontend/src/components/graph/
├── GraphCanvas.tsx             # 主画布
├── EntityNode.tsx              # 实体节点
├── RelationEdge.tsx            # 关系边
├── GraphToolbar.tsx            # 工具栏
├── GraphSearchBar.tsx          # 搜索
├── GraphFilters.tsx            # 过滤器
├── GraphDetailPanel.tsx        # 详情面板
└── GraphStats.tsx              # 统计

# 主页面
src/frontend/src/pages/SpaceDetailPage/GraphPage.tsx
```

---

## 🎨 G6 配置映射

### 节点大小

```typescript
// G6
size: (d) => Math.min(15 + d.data.degree * 5, 50)

// ReactFlow
const size = Math.min(60 + degree * 10, 150)
```

### Force 布局参数

```typescript
// G6 配置
{
  iterations: 150,
  link: { distance: 100, strength: 0.8 },
  charge: { strength: -400, distanceMax: 600 },
  center: { x: 0.5, y: 0.5, strength: 0.1 },
  preventOverlap: true
}

// D3 Force 映射
forceSimulation(nodes)
  .force('link', forceLink().distance(100).strength(0.8))
  .force('charge', forceManyBody().strength(-400).distanceMax(600))
  .force('center', forceCenter().strength(0.1))
  .force('collide', forceCollide())
  .tick(150)
```

### 颜色映射

```typescript
const ENTITY_TYPE_COLORS = {
  Person: '#5B8FF9',
  Organization: '#5AD8A6',
  Location: '#5D7092',
  Event: '#F6BD16',
  Product: '#E86452',
  Concept: '#6DC8EC',
  Technology: '#945FB9',
  Document: '#FF9845',
  Time: '#1E9493',
  Other: '#FF99C3',
}
```

---

## 🔌 后端 API 端点

### 实体 API

```bash
# 列表（分页）
GET /api/v1/entities/?space_id={id}&page=1&page_size=50

# 搜索
GET /api/v1/entities/?space_id={id}&search={query}

# 过滤类型
GET /api/v1/entities/?space_id={id}&entity_type=Person

# 单个实体
GET /api/v1/entities/{entity_id}
```

### 图谱 API

```bash
# 获取子图（BFS）
POST /api/v1/graphs/{space_id}/subgraph
Body: {
  "entity_ids": [1, 2, 3],
  "max_depth": 2,
  "max_nodes": 100
}

# 扩展邻居
GET /api/v1/graphs/{space_id}/entity/{entity_id}/relations?direction=both

# 统计信息
GET /api/v1/graphs/{space_id}/stats
```

---

## 💻 常用代码片段

### 使用 React Query Hook

```typescript
import { useGetSubgraphQuery } from '@/controllers/API/queries/graphs'

const { data, isLoading } = useGetSubgraphQuery(
  spaceId,
  { entity_ids: [1, 2, 3], max_depth: 2 }
)
```

### 使用 Zustand Store

```typescript
import { useGraphStore } from '@/stores/graphStore'

const {
  nodes,
  edges,
  selectedNode,
  setNodes,
  selectNode,
} = useGraphStore()
```

### 数据转换

```typescript
import {
  transformEntitiesToNodes,
  transformRelationsToEdges,
} from '@/utils/graph'

const nodes = transformEntitiesToNodes(entities, relations)
const edges = transformRelationsToEdges(relations)
```

### 应用布局

```typescript
import { applyForceLayout } from '@/utils/graph/layout-force'

const layoutedNodes = applyForceLayout(nodes, edges, {
  width: window.innerWidth,
  height: window.innerHeight - 200,
})
```

---

## 🐛 常见错误

### 1. 子图查询失败

**错误：** `entity_ids is required`

**原因：** 没有提供起始实体 ID

**解决：**
```typescript
// ❌ 错误
useGetSubgraphQuery(spaceId, { max_depth: 2 })

// ✅ 正确
useGetSubgraphQuery(spaceId, {
  entity_ids: [1, 2, 3],  // 必须提供
  max_depth: 2
})
```

---

### 2. 权限错误 403

**错误：** `Permission denied`

**原因：** 缺少 `DOCUMENTS_READ` 权限

**解决：** 在 API 拦截器中处理
```typescript
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 403) {
      toast({ title: 'Permission Denied', variant: 'destructive' })
    }
    return Promise.reject(error)
  }
)
```

---

### 3. 节点位置为 (0, 0)

**错误：** 所有节点堆叠在原点

**原因：** 忘记应用布局算法

**解决：**
```typescript
// ❌ 错误：直接使用转换后的节点
const nodes = transformEntitiesToNodes(entities)

// ✅ 正确：应用布局算法
const transformedNodes = transformEntitiesToNodes(entities)
const layoutedNodes = applyForceLayout(transformedNodes, edges)
```

---

## 🧪 测试命令

### 后端 API 测试

```bash
# 设置 Token
export TOKEN="your_access_token"

# 测试获取实体
curl -X GET "http://localhost:7860/api/v1/entities/?space_id=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# 测试获取子图
curl -X POST "http://localhost:7860/api/v1/graphs/1/subgraph" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"entity_ids": [1,2,3], "max_depth": 2, "max_nodes": 100}'

# 测试统计
curl -X GET "http://localhost:7860/api/v1/graphs/1/stats" \
  -H "Authorization: Bearer $TOKEN"
```

### 前端测试

```bash
# 启动开发服务器
make frontend

# 类型检查
cd src/frontend && npm run type-check

# Linting
make lint

# 格式化
make format_frontend
```

---

## 📦 依赖包

```json
{
  "dependencies": {
    "@xyflow/react": "^12.3.6",
    "@tanstack/react-query": "^5.90.7",
    "zustand": "^5.0.9",
    "dagre": "^0.8.5",
    "d3-force": "^3.0.0"
  },
  "devDependencies": {
    "@types/dagre": "^0.7.52"
  }
}
```

### 安装命令

```bash
cd src/frontend
npm install @xyflow/react dagre d3-force
npm install @types/dagre --save-dev
```

---

## 🚀 快速启动

```bash
# 1. 后端
make backend

# 2. 前端
make frontend

# 3. 创建分支
git checkout -b feature/knowledge-graph-frontend

# 4. 创建文件（使用文档中的代码）

# 5. 访问
http://localhost:3000/spaces/1/graph
```

---

## 📚 完整文档

1. **[YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)** - 完整技术方案
2. **[YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md](./YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md)** - 8 周清单
3. **[YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md](./YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md)** - 代码实现
4. **[YUXI_KNOW_GRAPH_LAYOUT_GUIDE.md](./YUXI_KNOW_GRAPH_LAYOUT_GUIDE.md)** - 布局算法
5. **[YUXI_KNOW_GRAPH_COMPONENTS_GUIDE.md](./YUXI_KNOW_GRAPH_COMPONENTS_GUIDE.md)** - UI 组件
6. **[YUXI_KNOW_GRAPH_MIGRATION_SUMMARY.md](./YUXI_KNOW_GRAPH_MIGRATION_SUMMARY.md)** - 文档汇总

---

**保存此文件到书签，开发时随时查阅！** 📌
