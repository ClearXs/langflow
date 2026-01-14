# Yuxi-Know 知识图谱前端迁移 - 文档汇总

> 完整的迁移规划和实施文档索引

**项目状态：** ✅ 后端完成 | 📋 前端规划完成 | ⏳ 等待实施

---

## 📚 文档列表

### 1. 核心规划文档

#### [YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md) (68KB)

**用途：** 完整的技术迁移方案和架构设计

**包含内容：**
- Yuxi-Know 源码深度分析（GraphCanvas.vue、useGraph composable）
- Langflow 后端 API 完整分析（graphs.py、entities.py）
- **CRITICAL：API 架构差异对比**（两步加载流程）
- React Query Hooks 完整实现
- 数据转换逻辑详解
- 错误处理和权限处理方案
- API 映射对照表

**适合对象：** 技术负责人、架构师

**关键发现：**
```
Yuxi-Know: GET /subgraph?node_label=*  (一步，通配符)
Langflow:  GET /entities + POST /subgraph  (两步，需entity_ids)
```

---

### 2. 实施清单

#### [YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md](./YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md)

**用途：** 8 周实施计划和任务清单

**包含内容：**
- 8 个阶段的详细任务分解
- 每个阶段的验收标准
- 风险评估和缓解措施
- 开发工具和命令参考
- 立即行动指南

**适合对象：** 项目经理、开发团队

**阶段划分：**
- ✅ 第 1 周：基础架构（类型、Hooks、Store）
- ✅ 第 2 周：数据转换层
- ✅ 第 3 周：自定义节点/边
- ✅ 第 4 周：核心画布组件
- ✅ 第 5 周：搜索和过滤
- ✅ 第 6 周：详情面板和扩展
- ✅ 第 7 周：统计和优化
- ✅ 第 8 周：集成和测试

---

### 3. 实施指南

#### [YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md](./YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md)

**用途：** 详细的代码实现指南

**包含内容：**
- 完整项目结构
- **类型定义完整实现**（EntityRead, RelationRead, GraphNode, GraphEdge）
- **React Query Hooks 完整实现**（useGetEntitiesQuery, useGetSubgraphQuery, useExpandNeighbors）
- **Zustand Store 完整实现**（graphStore.ts）
- **数据转换工具**（transform-entities.ts, transform-relations.ts）
- **颜色映射**（映射 G6 的 10 种颜色）

**适合对象：** 前端开发工程师

**关键代码文件：**
- `src/frontend/src/types/api/graphs.ts` - 所有类型定义
- `src/frontend/src/controllers/API/queries/graphs/` - API Hooks
- `src/frontend/src/stores/graphStore.ts` - 状态管理
- `src/frontend/src/utils/graph/` - 转换工具

---

### 4. 布局算法指南

#### [YUXI_KNOW_GRAPH_LAYOUT_GUIDE.md](./YUXI_KNOW_GRAPH_LAYOUT_GUIDE.md)

**用途：** 布局算法详细实现（映射 G6 Force 布局）

**包含内容：**
- **Dagre 层次布局实现**
- **D3 Force 力导向布局实现**（完全映射 G6 配置）
- **增量布局算法**（扩展邻居时使用）
- **自定义节点组件**（EntityNode.tsx）
- **自定义边组件**（RelationEdge.tsx）
- **主画布组件**（GraphCanvas.tsx）

**适合对象：** 前端开发工程师（图谱可视化）

**G6 配置映射：**
```typescript
// G6 Force 配置
{
  iterations: 150,
  link: { distance: 100, strength: 0.8 },
  charge: { strength: -400, distanceMax: 600 },
  center: { strength: 0.1 },
  preventOverlap: true
}

// 完全映射到 D3 Force
```

---

### 5. 组件完整实现指南

#### [YUXI_KNOW_GRAPH_COMPONENTS_GUIDE.md](./YUXI_KNOW_GRAPH_COMPONENTS_GUIDE.md)

**用途：** 所有 React 组件的完整实现代码

**包含内容：**
- **GraphToolbar.tsx** - 工具栏（缩放、布局切换、导出）
- **GraphSearchBar.tsx** - 搜索栏（实时搜索、下拉结果）
- **GraphFilters.tsx** - 过滤器（实体类型、关系类型、权重）
- **GraphDetailPanel.tsx** - 详情面板（扩展邻居、Focus）
- **GraphStats.tsx** - 统计面板（实体/关系分布）
- **GraphPage.tsx** - 主页面组件（集成所有功能）
- 路由配置

**适合对象：** 前端开发工程师（UI 组件）

**完整实施步骤：**
1. 安装依赖
2. 创建文件结构
3. 复制代码
4. 测试

---

## 🎯 技术栈对比

### 源系统（Yuxi-Know）

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5.21 | 前端框架 |
| AntV G6 | 5.0.49 | 图谱渲染 |
| Ant Design Vue | 4.2.6 | UI 组件 |
| D3 | 7.9.0 | Force 布局 |

### 目标系统（Langflow）

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.3.1 | 前端框架 |
| @xyflow/react | 12.3.6 | 图谱渲染 |
| shadcn/ui | latest | UI 组件 |
| Zustand | 5.0.9 | 状态管理 |
| React Query | 5.90.7 | API 管理 |
| Dagre | 0.8.5 | 层次布局 |
| D3 Force | latest | 力导向布局 |

---

## 🔑 关键技术决策

### 1. API 架构差异

**问题：** Yuxi-Know 支持通配符获取所有实体，Langflow 需要指定 entity_ids

**解决方案：** 两步加载流程

```typescript
// Step 1: 获取实体列表
GET /entities/?space_id=123&page_size=20

// Step 2: 使用前 N 个实体 ID 获取子图
POST /graphs/123/subgraph
Body: { entity_ids: [1,2,3,4,5], max_depth: 2 }
```

---

### 2. 布局算法选择

**问题：** ReactFlow 无内置布局，需手动实现

**解决方案：** 提供两种布局

- **Force 布局** - 映射 G6，保持视觉一致性（默认）
- **Dagre 布局** - 层次结构清晰

---

### 3. 状态管理

**问题：** Vue Composable 如何迁移到 React

**解决方案：** Zustand Store

```typescript
// Yuxi-Know (Vue Composable)
const { graphData, selectedItem, showDetailDrawer } = useGraph()

// Langflow (Zustand Store)
const { nodes, edges, selectedNode, showDetailPanel } = useGraphStore()
```

---

### 4. 颜色映射

**问题：** 保持与 G6 版本视觉一致

**解决方案：** 完全映射 G6 的 10 种实体类型颜色

```typescript
const ENTITY_TYPE_COLORS = {
  Person: '#5B8FF9',
  Organization: '#5AD8A6',
  Location: '#5D7092',
  // ... 10 种颜色
}
```

---

## 📁 项目文件结构

```
src/frontend/src/
├── types/api/graphs.ts                          ✅ 类型定义
├── controllers/API/queries/graphs/
│   ├── use-get-entities.ts                      ✅ 获取实体
│   ├── use-get-subgraph.ts                      ✅ 获取子图
│   ├── use-expand-neighbors.ts                  ✅ 扩展邻居
│   ├── use-get-graph-stats.ts                   ✅ 获取统计
│   └── index.ts                                 ✅ 导出
├── stores/graphStore.ts                         ✅ 状态管理
├── utils/graph/
│   ├── transform-entities.ts                    ✅ 实体转换
│   ├── transform-relations.ts                   ✅ 关系转换
│   ├── layout-dagre.ts                          ✅ Dagre 布局
│   ├── layout-force.ts                          ✅ Force 布局
│   ├── layout-incremental.ts                    ✅ 增量布局
│   ├── colors.ts                                ✅ 颜色映射
│   └── index.ts                                 ✅ 导出
├── components/graph/
│   ├── EntityNode.tsx                           ✅ 实体节点
│   ├── RelationEdge.tsx                         ✅ 关系边
│   ├── GraphCanvas.tsx                          ✅ 主画布
│   ├── GraphToolbar.tsx                         ✅ 工具栏
│   ├── GraphSearchBar.tsx                       ✅ 搜索栏
│   ├── GraphFilters.tsx                         ✅ 过滤器
│   ├── GraphDetailPanel.tsx                     ✅ 详情面板
│   ├── GraphStats.tsx                           ✅ 统计面板
│   ├── node-types.ts                            ✅ 节点类型注册
│   └── index.ts                                 ✅ 导出
└── pages/SpaceDetailPage/GraphPage.tsx          ✅ 主页面
```

**状态：** ✅ 所有文件代码已提供

---

## 🚀 立即开始实施

### 快速启动命令

```bash
# 1. 启动后端
make backend

# 2. 启动前端
make frontend

# 3. 创建开发分支
git checkout -b feature/knowledge-graph-frontend

# 4. 安装依赖
cd src/frontend
npm install @xyflow/react dagre d3-force
npm install @types/dagre --save-dev

# 5. 创建文件结构
bash <<'EOF'
touch src/types/api/graphs.ts
mkdir -p src/controllers/API/queries/graphs
touch src/controllers/API/queries/graphs/{use-get-entities,use-get-subgraph,use-expand-neighbors,use-get-graph-stats,index}.ts
touch src/stores/graphStore.ts
mkdir -p src/utils/graph
touch src/utils/graph/{transform-entities,transform-relations,layout-dagre,layout-force,layout-incremental,colors,index}.ts
mkdir -p src/components/graph
touch src/components/graph/{EntityNode,RelationEdge,GraphCanvas,GraphToolbar,GraphSearchBar,GraphFilters,GraphDetailPanel,GraphStats,node-types,index}.tsx
touch src/pages/SpaceDetailPage/GraphPage.tsx
EOF

# 6. 复制代码（从文档中复制到对应文件）

# 7. 测试
# 访问 http://localhost:3000/spaces/1/graph
```

---

### 第一周任务清单

- [ ] **Day 1-2：基础架构**
  - [ ] 创建 `types/api/graphs.ts`
  - [ ] 创建 `stores/graphStore.ts`
  - [ ] 测试 Zustand store 是否正常工作

- [ ] **Day 3-4：API Hooks**
  - [ ] 创建 `use-get-entities.ts`
  - [ ] 创建 `use-get-subgraph.ts`
  - [ ] 测试与后端 API 连接

- [ ] **Day 5：数据转换**
  - [ ] 创建 `transform-entities.ts`
  - [ ] 创建 `transform-relations.ts`
  - [ ] 创建 `colors.ts`
  - [ ] 测试数据转换逻辑

**验收标准：**
- ✅ TypeScript 无错误
- ✅ API 调用成功返回数据
- ✅ Store 状态正确更新
- ✅ 数据转换输出正确格式

---

## 📊 进度跟踪

### 已完成 ✅

- [x] 深度分析 Yuxi-Know 源码
- [x] 完整分析 Langflow 后端 API
- [x] 识别 API 架构差异
- [x] 设计两步加载流程
- [x] 编写完整迁移计划
- [x] 创建 8 周实施清单
- [x] 提供所有文件的完整代码
- [x] 提供布局算法实现
- [x] 提供组件实现
- [x] 创建文档索引

### 待完成 ⏳

- [ ] 创建实际文件
- [ ] 复制代码到文件
- [ ] 安装依赖
- [ ] 测试后端 API 连接
- [ ] 实现第一个工作原型
- [ ] 迭代开发 8 周

---

## 🔧 开发环境

### 要求

- Node.js v22.12 LTS
- npm v10.9
- Python 3.x (后端)
- PostgreSQL (生产环境)

### 端口

- 后端：http://localhost:7860
- 前端：http://localhost:3000
- API 文档：http://localhost:7860/api/v1/docs

---

## 📖 参考资源

### 官方文档

- **ReactFlow:** https://reactflow.dev/
- **React Query:** https://tanstack.com/query/latest
- **Zustand:** https://zustand-demo.pmnd.rs/
- **Dagre:** https://github.com/dagrejs/dagre
- **D3 Force:** https://d3js.org/d3-force

### Langflow 文档

- **API 文档:** http://localhost:7860/api/v1/docs
- **开发指南:** [CLAUDE.md](./CLAUDE.md)

---

## ❓ 常见问题

### Q: 为什么需要两步加载？

**A:** Langflow 的子图端点需要指定 `entity_ids`，不支持 Yuxi-Know 的通配符 `node_label="*"`。因此需要先获取实体列表，再请求子图。

---

### Q: 如何保持与 G6 版本的视觉一致性？

**A:** 通过完全映射 G6 的配置参数：
- 节点大小：`Math.min(15 + degree * 5, 50)`
- Force 参数：`linkDistance: 100, chargeStrength: -400` 等
- 颜色映射：10 种实体类型颜色

---

### Q: 性能如何优化？

**A:**
- React Query 缓存（30s - 2min）
- 虚拟化渲染（大图谱）
- Web Worker 布局计算
- 增量布局（仅对新节点）

---

### Q: 如何测试后端 API？

**A:**
```bash
# 获取实体
curl -X GET "http://localhost:7860/api/v1/entities/?space_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取子图
curl -X POST "http://localhost:7860/api/v1/graphs/1/subgraph" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"entity_ids": [1,2,3], "max_depth": 2}'
```

---

## 📞 联系方式

**文档维护：** Langflow Team
**更新日期：** 2026-01-09
**版本：** 1.0
**状态：** ✅ 文档完成，⏳ 等待实施

---

## 🎉 下一步

选择以下任一方案开始：

1. **立即实施** - 运行快速启动命令，创建文件，开始开发
2. **先验证后端** - 测试后端 API 是否正常
3. **团队评审** - 分享文档给团队，讨论方案
4. **调整计划** - 根据反馈修改文档

**推荐：** 先创建基础架构文件（第 1 周任务），验证技术可行性，再全面实施。

---

**所有文档已就绪，随时可以开始实施！** 🚀
