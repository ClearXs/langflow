# Yuxi-Know 知识图谱前端迁移执行清单

> 基于完整迁移计划：[YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)

## 🎯 迁移概览

**源系统：** Yuxi-Know (Vue 3 + AntV G6)
**目标系统：** Langflow (React 18 + ReactFlow)
**预计周期：** 8 周
**状态：** ✅ 后端已完成，📋 前端规划完成，⏳ 待实施

---

## ✅ 已完成工作

- [x] **后端迁移完成**
  - Entity/Relation 模型已建立
  - Graph API 端点已实现（子图查询、邻居扩展、统计）
  - RBAC 权限控制集成
  - BFS 子图遍历算法实现

- [x] **源码深度分析**
  - Yuxi-Know 完整代码审查（GraphCanvas.vue、useGraph composable）
  - G6 配置完整提取（布局、样式、交互）
  - Langflow 后端 API 完整理解

- [x] **迁移方案设计**
  - API 架构差异识别
  - 数据流重新设计（两步加载流程）
  - React Query hooks 方案
  - 组件架构设计

---

## 🔴 关键 API 架构差异（必读）

### Yuxi-Know vs Langflow

| 特性 | Yuxi-Know | Langflow | 迁移影响 |
|------|-----------|----------|---------|
| **获取图谱** | `GET /subgraph?node_label=*` | `POST /graphs/{space_id}/subgraph` | ⚠️ **需要两步流程** |
| **起始节点** | 支持通配符 `*` | 必须提供 `entity_ids: [1,2,3]` | ⚠️ **需先获取实体列表** |
| **响应格式** | `{nodes, edges}` | `{entities, relations}` | ⚠️ **字段名不同** |

### 关键实现：两步数据加载

```typescript
// ❌ Yuxi-Know 方式（一步）
GET /api/graph/subgraph?node_label=*&max_depth=2

// ✅ Langflow 方式（两步）
// Step 1: 获取实体列表
GET /entities/?space_id=123&page=1&page_size=20
// Step 2: 使用实体 ID 获取子图
POST /graphs/123/subgraph
Body: { entity_ids: [1,2,3,4,5], max_depth: 2, max_nodes: 100 }
```

---

## 📋 实施阶段清单

### 阶段 1：基础设施（第 1 周）

**目标：** 搭建项目基础架构

- [ ] **1.1 创建类型定义**
  - [ ] `/src/frontend/src/types/api/graphs.ts`
    - `EntityRead` - 实体类型
    - `RelationRead` - 关系类型
    - `SubgraphRequest` - 子图请求
    - `SubgraphResponse` - 子图响应
    - `GraphStatsResponse` - 统计响应

- [ ] **1.2 创建 React Query Hooks**
  - [ ] `/src/frontend/src/controllers/API/queries/graphs/use-get-entities.ts`
    - 实现 `useGetEntitiesQuery(space_id, filters)`
  - [ ] `/src/frontend/src/controllers/API/queries/graphs/use-get-subgraph.ts`
    - 实现 `useGetSubgraphQuery(space_id, entity_ids)`
  - [ ] `/src/frontend/src/controllers/API/queries/graphs/use-expand-neighbors.ts`
    - 实现 `useExpandNeighbors()` mutation
  - [ ] `/src/frontend/src/controllers/API/queries/graphs/use-get-graph-stats.ts`
    - 实现 `useGetGraphStatsQuery(space_id)`

- [ ] **1.3 创建 Zustand Store**
  - [ ] `/src/frontend/src/stores/graphStore.ts`
    ```typescript
    interface GraphStore {
      nodes: Node[]
      edges: Edge[]
      selectedNode: Node | null
      selectedEntityIds: number[]
      setNodes: (nodes: Node[]) => void
      setEdges: (edges: Edge[]) => void
      addNodes: (nodes: Node[]) => void
      addEdges: (edges: Edge[]) => void
      selectNode: (node: Node | null) => void
      setSelectedEntityIds: (ids: number[]) => void
      reset: () => void
    }
    ```

- [ ] **1.4 安装依赖**
  ```bash
  cd src/frontend
  npm install @xyflow/react dagre
  ```

**验收标准：**
- ✅ TypeScript 类型无错误
- ✅ Hooks 单元测试通过
- ✅ Store 能正确管理状态

---

### 阶段 2：数据转换层（第 2 周）

**目标：** 实现 Langflow API → ReactFlow 数据转换

- [ ] **2.1 实体转节点**
  - [ ] `/src/frontend/src/utils/graph/transform-entities.ts`
    ```typescript
    function transformEntitiesToNodes(entities: EntityRead[]): Node[] {
      return entities.map(entity => ({
        id: String(entity.id),
        type: 'entityNode',
        position: { x: 0, y: 0 },  // 待布局
        data: {
          label: entity.name,
          entityType: entity.entity_type,
          description: entity.description,
          properties: entity.properties,
          original: entity,
        }
      }))
    }
    ```

- [ ] **2.2 关系转边**
  - [ ] `/src/frontend/src/utils/graph/transform-relations.ts`
    ```typescript
    function transformRelationsToEdges(relations: RelationRead[]): Edge[] {
      return relations.map(relation => ({
        id: `e-${relation.id}`,
        source: String(relation.source_entity_id),
        target: String(relation.target_entity_id),
        type: 'relationEdge',
        label: relation.relation_type,
        animated: relation.weight > 0.8,
        data: {
          relationType: relation.relation_type,
          weight: relation.weight,
          description: relation.description,
          original: relation,
        }
      }))
    }
    ```

- [ ] **2.3 布局算法**
  - [ ] `/src/frontend/src/utils/graph/layout-dagre.ts`
    - 实现 Dagre 层次布局
  - [ ] `/src/frontend/src/utils/graph/layout-force.ts`
    - 实现 D3 Force 力导向布局（兼容 G6）
  - [ ] 实现增量布局（仅对新节点）

**验收标准：**
- ✅ 实体/关系正确转换为 ReactFlow 格式
- ✅ 布局算法正常工作，无节点重叠
- ✅ 增量布局平滑添加新节点

---

### 阶段 3：自定义节点/边（第 3 周）

**目标：** 实现 G6 风格的可视化组件

- [ ] **3.1 实体节点组件**
  - [ ] `/src/frontend/src/components/graph/EntityNode.tsx`
    ```typescript
    // 功能需求：
    // - 圆形节点（映射 G6 circle）
    // - 根据 degree 动态调整大小
    // - 10 种实体类型颜色（映射 G6 colorMap）
    // - Hover 高亮效果
    // - 支持拖拽
    // - Handle 连接点
    ```

- [ ] **3.2 关系边组件**
  - [ ] `/src/frontend/src/components/graph/RelationEdge.tsx`
    ```typescript
    // 功能需求：
    // - 贝塞尔曲线（映射 G6 quadratic）
    // - 箭头（endArrow）
    // - 边标签（relation_type）
    // - 根据 weight 调整透明度/粗细
    // - Hover 高亮效果
    ```

- [ ] **3.3 节点类型注册**
  - [ ] `/src/frontend/src/components/graph/node-types.ts`
    ```typescript
    export const nodeTypes = {
      entityNode: EntityNode,
    }
    export const edgeTypes = {
      relationEdge: RelationEdge,
    }
    ```

**验收标准：**
- ✅ 节点视觉效果与 G6 版本一致
- ✅ 交互行为正常（hover、select、drag）
- ✅ 性能良好（100+ 节点无卡顿）

---

### 阶段 4：核心画布组件（第 4 周）

**目标：** 实现主图谱画布

- [ ] **4.1 GraphCanvas 组件**
  - [ ] `/src/frontend/src/components/graph/GraphCanvas.tsx`
    ```typescript
    // 功能需求：
    // - 集成 ReactFlow
    // - 渲染节点/边
    // - Controls（缩放、全屏）
    // - MiniMap（小地图）
    // - Background（网格背景）
    // - 节点点击事件 → 打开详情面板
    // - 节点拖拽
    // - 画布平移/缩放
    ```

- [ ] **4.2 工具栏**
  - [ ] `/src/frontend/src/components/graph/GraphToolbar.tsx`
    ```typescript
    // 功能需求：
    // - 缩放控制（+/-）
    // - 自适应（Fit View）
    // - 布局切换（Dagre/Force）
    // - 导出图片
    // - 刷新数据
    ```

- [ ] **4.3 初始数据加载**
  - [ ] 实现两步加载流程
    ```typescript
    // Step 1: 获取前 20 个实体
    const { data: entities } = useGetEntitiesQuery({ space_id, page_size: 20 })

    // Step 2: 取前 10 个实体 ID，获取子图
    const startingIds = entities?.items.slice(0, 10).map(e => e.id) || []
    const { data: subgraph } = useGetSubgraphQuery(space_id, {
      entity_ids: startingIds,
      max_depth: 2
    })
    ```

**验收标准：**
- ✅ 图谱正常渲染，数据正确
- ✅ 所有控件功能正常
- ✅ 加载状态和错误处理完善

---

### 阶段 5：搜索和过滤（第 5 周）

**目标：** 实现实体搜索和高亮

- [ ] **5.1 搜索栏组件**
  - [ ] `/src/frontend/src/components/graph/GraphSearchBar.tsx`
    ```typescript
    // 功能需求：
    // - 实时搜索（防抖）
    // - 搜索结果下拉列表
    // - 选中实体 → 更新图谱
    // - 显示实体类型 Badge
    ```

- [ ] **5.2 关键词高亮**
  - [ ] 实现节点高亮逻辑
    ```typescript
    // 映射 G6 highlightKeywordNodes 功能
    // - 搜索关键词匹配 entity.name
    // - 高亮匹配节点（边框、颜色）
    // - 聚焦到第一个匹配节点
    ```

- [ ] **5.3 实体类型过滤**
  - [ ] `/src/frontend/src/components/graph/GraphFilters.tsx`
    ```typescript
    // 功能需求：
    // - 多选实体类型
    // - 过滤显示/隐藏节点
    // - 统计各类型数量
    ```

**验收标准：**
- ✅ 搜索响应快速（< 300ms）
- ✅ 高亮效果清晰
- ✅ 过滤功能正常

---

### 阶段 6：详情面板和扩展（第 6 周）

**目标：** 实现实体详情和邻居扩展

- [ ] **6.1 详情面板**
  - [ ] `/src/frontend/src/components/graph/GraphDetailPanel.tsx`
    ```typescript
    // 功能需求（映射 G6 DetailDrawer）：
    // - 显示实体名称、类型
    // - 显示描述、别名
    // - 显示自定义属性（properties）
    // - 显示度数（degree）
    // - "Expand Neighbors" 按钮
    // - "Focus Neighbor" 按钮
    // - 链接到源文档（document_id）
    ```

- [ ] **6.2 扩展邻居功能**
  - [ ] 实现 `useExpandNeighbors` hook 调用
    ```typescript
    // 流程：
    // 1. 调用 GET /graphs/{space_id}/entity/{entity_id}/relations
    // 2. 提取新 entity_ids
    // 3. 调用 GET /entities/{id} 获取实体详情
    // 4. 转换为节点/边
    // 5. 应用增量布局
    // 6. 添加到画布
    ```

- [ ] **6.3 Focus Neighbor**
  - [ ] 实现高亮邻居节点
    ```typescript
    // 映射 G6 focusNeighbor 功能
    // - 高亮直接相连节点
    // - 淡化其他节点
    // - 聚焦到选中节点区域
    ```

**验收标准：**
- ✅ 详情面板显示完整信息
- ✅ 扩展邻居正常工作
- ✅ Focus 效果清晰

---

### 阶段 7：统计和优化（第 7 周）

**目标：** 添加统计信息和性能优化

- [ ] **7.1 统计面板**
  - [ ] `/src/frontend/src/components/graph/GraphStats.tsx`
    ```typescript
    // 调用 GET /graphs/{space_id}/stats
    // 显示：
    // - 总实体数 / 关系数
    // - 实体类型分布（饼图）
    // - 关系类型分布（柱状图）
    ```

- [ ] **7.2 性能优化**
  - [ ] 实现虚拟化渲染（大图谱）
  - [ ] 添加节点聚类（100+ 节点时）
  - [ ] 优化布局算法性能
  - [ ] 添加 Web Worker 计算布局

- [ ] **7.3 空状态和错误处理**
  - [ ] 无数据时显示引导
  - [ ] 403 权限错误处理
  - [ ] 加载失败重试机制
  - [ ] 网络错误提示

**验收标准：**
- ✅ 统计数据准确
- ✅ 500+ 节点无明显卡顿
- ✅ 错误处理完善

---

### 阶段 8：集成和测试（第 8 周）

**目标：** 完整集成和测试

- [ ] **8.1 路由集成**
  - [ ] 添加路由 `/spaces/:spaceId/graph`
  - [ ] 在 Space Detail 页面添加 "Knowledge Graph" 标签

- [ ] **8.2 权限集成**
  - [ ] 检查 `DOCUMENTS_READ` 权限
  - [ ] 无权限时显示提示

- [ ] **8.3 页面组装**
  - [ ] `/src/frontend/src/pages/SpaceDetailPage/GraphPage.tsx`
    ```typescript
    export default function GraphPage() {
      return (
        <div className="h-full flex flex-col">
          {/* 顶部工具栏 */}
          <div className="flex items-center gap-4 p-4 border-b">
            <GraphSearchBar />
            <GraphFilters />
            <GraphToolbar />
          </div>

          {/* 主画布 */}
          <div className="flex-1 relative">
            <GraphCanvas />
            <GraphStats />  {/* 右下角 */}
          </div>

          {/* 详情面板（Sheet） */}
          <GraphDetailPanel />
        </div>
      )
    }
    ```

- [ ] **8.4 测试**
  - [ ] 单元测试（hooks、utils）
  - [ ] 集成测试（完整流程）
  - [ ] E2E 测试（Playwright）
  - [ ] 浏览器兼容性测试
  - [ ] 性能测试（大图谱）

**验收标准：**
- ✅ 所有功能正常工作
- ✅ 测试覆盖率 > 80%
- ✅ 无明显 bug

---

## 🔧 开发工具和命令

### 启动开发环境

```bash
# 后端（必须先启动）
make backend  # http://localhost:7860

# 前端
make frontend  # http://localhost:3000
```

### 代码质量

```bash
# 格式化
make format_frontend

# Linting
make lint

# 类型检查
cd src/frontend && npm run type-check
```

### 测试

```bash
# 单元测试
cd src/frontend && npm run test

# E2E 测试
cd src/frontend && npm run test:e2e
```

---

## 📦 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `@xyflow/react` | 12.3.6 | ReactFlow 图谱渲染 |
| `dagre` | 0.8.5 | 层次布局算法 |
| `@tanstack/react-query` | 5.90.7 | API 数据管理 |
| `zustand` | 5.0.9 | 状态管理 |
| `tailwindcss` | 3.4.17 | 样式 |

---

## 🚨 风险和注意事项

### 高风险项

1. **API 两步加载性能**
   - 问题：需要两次 API 调用才能显示图谱
   - 缓解：并行请求、React Query 缓存、Loading 状态优化

2. **大图谱性能**
   - 问题：500+ 节点可能卡顿
   - 缓解：虚拟化渲染、节点聚类、Web Worker 布局

3. **布局算法差异**
   - 问题：ReactFlow 布局与 G6 Force 布局可能不同
   - 缓解：调整参数、实现自定义布局、用户可选择

### 中风险项

1. **权限处理**
   - 确保所有 API 调用都处理 403 错误
   - 提供清晰的权限提示

2. **数据一致性**
   - 扩展邻居后，确保无重复节点/边
   - 正确更新 React Query 缓存

---

## 📚 参考文档

- **完整迁移计划：** [YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)
- **ReactFlow 文档：** https://reactflow.dev/
- **React Query 文档：** https://tanstack.com/query/latest
- **Dagre 文档：** https://github.com/dagrejs/dagre
- **Langflow API：** http://localhost:7860/api/v1/docs

---

## ✅ 下一步行动

**立即开始：**

1. 创建 GraphPage 基础结构
2. 实现类型定义
3. 创建第一个 React Query hook (`useGetEntitiesQuery`)
4. 测试与后端 API 连接

**命令：**

```bash
# 1. 启动后端
make backend

# 2. 启动前端
make frontend

# 3. 创建分支
git checkout -b feature/knowledge-graph-frontend

# 4. 开始开发
# - 创建 src/frontend/src/types/api/graphs.ts
# - 创建 src/frontend/src/controllers/API/queries/graphs/use-get-entities.ts
# - 创建 src/frontend/src/stores/graphStore.ts
```

---

**文档版本：** 1.0
**更新日期：** 2026-01-09
**维护者：** Langflow Team
**状态：** ✅ 后端完成 | 📋 前端规划完成 | ⏳ 等待实施
