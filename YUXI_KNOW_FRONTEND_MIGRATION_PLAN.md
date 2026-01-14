# SurfSense 组件迁移计划

## 执行摘要

基于对 SurfSense 和 Langflow 组件系统的全面分析以及与用户的头脑风暴确认，本计划旨在将 SurfSense 的所有组件迁移到 Langflow，采用以下核心策略：

**核心决策：**
1. **UI 组件策略**：仅迁移 Langflow 缺失的 UI 组件（avatar, calendar, sonner 等），其余复用 Langflow 现有组件
2. **聊天组件策略**：完整迁移 assistant-ui/thread.tsx 及相关组件，添加 @assistant-ui/react 依赖
3. **状态管理策略**：直接将所有 Jotai atoms 转换为 Zustand stores，不安装 jotai 依赖
4. **依赖版本策略**：保持 Langflow 现有版本，仅选择性升级低风险依赖
5. **迁移顺序**：先迁移 UI 组件，再迁移业务逻辑组件
6. **目录结构**：所有组件集成到 Langflow 现有目录结构
7. **依赖添加**：一次性安装所有必需依赖
8. **迁移范围**：迁移所有 SurfSense 组件，后续由用户决定删除不需要的

## 一、组件对比分析

### SurfSense 组件清单（按目录）

#### 1. **ui/** - 基础 UI 组件（36个）
**完全基于 shadcn/ui + Radix UI**

| 组件类别 | SurfSense 组件 | Langflow 对应组件 | 迁移策略 |
|---------|--------------|----------------|---------|
| **表单控件** | button, input, textarea, checkbox, select, switch, label, form | ✅ 完全存在 | **无需迁移** |
| **布局组件** | card, separator, accordion, collapsible, tabs, sidebar | ✅ 完全存在 | **无需迁移** |
| **反馈组件** | alert, alert-dialog, dialog, tooltip, sonner | ⚠️ 缺少 sonner | **需添加依赖** |
| **导航组件** | breadcrumb, tabs, dropdown-menu, command, pagination | ✅ 基本存在 | **无需迁移** |
| **数据展示** | table, avatar, badge, progress, skeleton | ⚠️ 缺少 avatar | **需迁移 avatar** |
| **交互组件** | popover, scroll-area, calendar, slider | ⚠️ 缺少 calendar | **需迁移 calendar** |
| **特效组件** | bento-grid, spotlight, tilt | ❌ 不存在 | **需迁移** |

#### 2. **assistant-ui/** - AI 助手组件（7个）
**核心聊天界面组件**

| 组件 | 行数 | 依赖库 | Langflow 对应 | 策略 |
|------|------|--------|-------------|------|
| `thread.tsx` | 1092 | @assistant-ui/react | ❌ 不存在 | **核心组件 - 必须迁移** |
| `thread-list.tsx` | - | @assistant-ui/react | ❌ 不存在 | **必须迁移** |
| `attachment.tsx` | - | 自定义 | ❌ 不存在 | **必须迁移** |
| `inline-citation.tsx` | - | 自定义 | ❌ 不存在 | **必须迁移** |
| `markdown-text.tsx` | - | react-markdown | ✅ 有 react-markdown | **需适配** |
| `tool-fallback.tsx` | - | 自定义 | ❌ 不存在 | **必须迁移** |
| `tooltip-icon-button.tsx` | - | Radix UI | ✅ 可复用 Langflow | **无需迁移** |

#### 3. **sidebar/** - 侧边栏组件（9个）

| 组件 | 行数 | Langflow 对应 | 策略 |
|------|------|-------------|------|
| `app-sidebar.tsx` | 474 | ✅ sidebarComponent | **对比功能后决定** |
| `nav-main.tsx` | - | ✅ 部分功能存在 | **增强现有组件** |
| `nav-chats.tsx` | - | ❌ 不存在 | **必须迁移** |
| `nav-notes.tsx` | - | ❌ 不存在 | **必须迁移** |
| `nav-secondary.tsx` | - | ✅ 可复用 | **无需迁移** |
| `all-chats-sidebar.tsx` | - | ❌ 不存在 | **必须迁移** |
| `all-notes-sidebar.tsx` | - | ❌ 不存在 | **必须迁移** |
| `page-usage-display.tsx` | - | ❌ 不存在 | **必须迁移** |
| `AppSidebarProvider.tsx` | - | ❌ 不存在 | **必须迁移（状态管理）** |

#### 4. **new-chat/** - 聊天功能组件（5个）

| 组件 | 行数 | Langflow 对应 | 策略 |
|------|------|-------------|------|
| `chat-header.tsx` | - | ❌ 不存在 | **必须迁移** |
| `model-selector.tsx` | 388 | ❌ 不存在 | **必须迁移（核心功能）** |
| `model-config-sidebar.tsx` | - | ❌ 不存在 | **必须迁移** |
| `DocumentsDataTable.tsx` | - | ✅ 有 table 组件 | **基于现有 table 实现** |
| `source-detail-panel.tsx` | - | ❌ 不存在 | **必须迁移** |

#### 5. **sources/** - 数据源组件（6个）

| 组件 | Langflow 对应 | 策略 |
|------|-------------|------|
| `ConnectorsTab.tsx` | ❌ 不存在 | **必须迁移** |
| `DocumentUploadTab.tsx` | ✅ 有文件上传 | **增强现有功能** |
| `YouTubeTab.tsx` | ❌ 不存在 | **必须迁移** |
| `GridPattern.tsx` | ❌ 不存在 | **必须迁移** |
| `connector-data.tsx` | ❌ 不存在 | **配置数据 - 必须迁移** |

#### 6. **tool-ui/** - 工具 UI 组件（10个）

| 组件 | 说明 | 策略 |
|------|------|------|
| `article/` | 文章展示 | **必须迁移** |
| `audio.tsx` | 音频播放 | **必须迁移** |
| `deepagent-thinking.tsx` | 思考过程展示 | **核心功能 - 必须迁移** |
| `display-image.tsx` | 图片展示 | **必须迁移** |
| `generate-podcast.tsx` | 播客生成 | **必须迁移** |
| `image/` | 图片组件 | ✅ 有 ImageViewer | **对比后决定** |
| `link-preview.tsx` | 链接预览 | **必须迁移** |
| `media-card/` | 媒体卡片 | **必须迁移** |
| `scrape-webpage.tsx` | 网页抓取展示 | **必须迁移** |

#### 7. **settings/** - 设置组件（3个）

| 组件 | 行数 | Langflow 对应 | 策略 |
|------|------|-------------|------|
| `model-config-manager.tsx` | 500 | ❌ 不存在 | **核心配置组件 - 必须迁移** |
| `llm-role-manager.tsx` | - | ❌ 不存在 | **必须迁移** |
| `prompt-config-manager.tsx` | - | ❌ 不存在 | **必须迁移** |

#### 8. **其他组件**

| 目录/组件 | 数量 | 策略 |
|----------|------|------|
| `homepage/` | 7 | **必须迁移（全部迁移）** |
| `editConnector/` | 5 | **必须迁移** |
| `pricing/` | 1 | **必须迁移（全部迁移）** |
| `contact/` | 1 | **必须迁移（全部迁移）** |
| `providers/` | 1 | **必须迁移（I18nProvider）** |
| `theme/` | 2 | ✅ Langflow 已有 | **无需迁移** |

#### 9. **根目录组件**（14个）

| 组件 | Langflow 对应 | 策略 |
|------|-------------|------|
| `BlockNoteEditor.tsx` | ❌ 不存在 | **核心功能 - 必须迁移** |
| `DynamicBlockNoteEditor.tsx` | ❌ 不存在 | **必须迁移** |
| `LanguageSwitcher.tsx` | ❌ 不存在 | **必须迁移** |
| `Logo.tsx` | ✅ 存在 | **无需迁移** |
| `TokenHandler.tsx` | ✅ 有认证系统 | **适配现有系统** |
| `UserDropdown.tsx` | ✅ 可能存在 | **检查后决定** |
| `announcement-banner.tsx` | ❌ 不存在 | **必须迁移** |
| `copy-button.tsx` | ❌ 不存在 | **工具组件 - 迁移** |
| `dashboard-breadcrumb.tsx` | ✅ 有 breadcrumb | **增强现有组件** |
| `document-viewer.tsx` | ✅ 有查看器 | **对比后决定** |
| `inference-params-editor.tsx` | ❌ 不存在 | **必须迁移** |
| `json-metadata-viewer.tsx` | ✅ 有 JSON viewer | **对比后决定** |
| `markdown-viewer.tsx` | ✅ 有 react-markdown | **对比后决定** |
| `pricing.tsx` | - | **必须迁移** |
| `search-space-form.tsx` | ❌ 不存在 | **必须迁移** |

## 二、依赖管理分析

### 需要添加的核心依赖

#### 高优先级（必需）

```json
{
  "@assistant-ui/react": "^0.11.53",
  "@assistant-ui/react-markdown": "^0.11.9",
  "@blocknote/core": "^0.45.0",
  "@blocknote/mantine": "^0.45.0",
  "@blocknote/react": "^0.45.0",
  "@radix-ui/react-avatar": "^1.1.10",
  "sonner": "^2.0.6",
  "react-day-picker": "^9.8.1",
  "react-dropzone": "^14.3.8",
  "jotai": "^2.15.1"
}
```

#### 中等优先级（建议）

```json
{
  "@tanstack/react-table": "^8.21.3",
  "@tanstack/react-query-devtools": "^5.90.2",
  "@number-flow/react": "^0.5.10",
  "canvas-confetti": "^1.9.3",
  "motion": "^12.23.22"
}
```

#### 需要升级的现有依赖

```json
{
  "zustand": "^5.0.9",  // 从 4.5.2 升级
  "zod": "^4.2.1",      // 从 3.23.8 升级（需测试兼容性）
  "@tanstack/react-query": "^5.90.7",  // 从 5.49.2 升级
  "tailwind-merge": "^3.3.1"  // 从 2.6.0 升级
}
```

### 依赖冲突风险评估

**高风险：**
- React 版本差异（19.2.3 vs 18.3.1）- **建议保持 Langflow 现有版本**
- Tailwind CSS 版本（4.1.11 vs 3.4.4）- **v4 有重大破坏性变更，建议暂不升级**

**中等风险：**
- Zod v3 → v4 - 需要测试 schema 兼容性
- Zustand v4 → v5 - 破坏性变更较少

**低风险：**
- @tanstack/react-query 升级 - 向后兼容
- tailwind-merge 升级 - 向后兼容

## 三、迁移优先级分级

### P0 - 核心功能组件（必须迁移）

**影响：** 直接影响应用核心功能

1. **AI 聊天系统**
   - `assistant-ui/thread.tsx` (1092行)
   - `assistant-ui/thread-list.tsx`
   - `assistant-ui/attachment.tsx`
   - `assistant-ui/inline-citation.tsx`
   - `new-chat/model-selector.tsx` (388行)
   - `new-chat/chat-header.tsx`
   - `new-chat/model-config-sidebar.tsx`

2. **富文本编辑器**
   - `BlockNoteEditor.tsx` (167行)
   - `DynamicBlockNoteEditor.tsx`

3. **设置与配置**
   - `settings/model-config-manager.tsx` (500行)
   - `settings/llm-role-manager.tsx`
   - `settings/prompt-config-manager.tsx`
   - `inference-params-editor.tsx`

4. **搜索空间管理**
   - `search-space-form.tsx`

### P1 - 重要功能组件（高优先级迁移）

**影响：** 影响用户体验和功能完整性

1. **侧边栏导航**
   - `sidebar/nav-chats.tsx`
   - `sidebar/nav-notes.tsx`
   - `sidebar/all-chats-sidebar.tsx`
   - `sidebar/all-notes-sidebar.tsx`
   - `sidebar/AppSidebarProvider.tsx`

2. **数据源管理**
   - `sources/ConnectorsTab.tsx`
   - `sources/YouTubeTab.tsx`
   - `sources/connector-data.tsx`
   - `editConnector/` 所有组件

3. **工具 UI**
   - `tool-ui/deepagent-thinking.tsx`
   - `tool-ui/article/`
   - `tool-ui/media-card/`

4. **国际化**
   - `LanguageSwitcher.tsx`
   - `providers/I18nProvider.tsx`

### P2 - 增强功能组件（中优先级迁移）

**影响：** 提升用户体验

1. **文档处理**
   - `new-chat/DocumentsDataTable.tsx`
   - `new-chat/source-detail-panel.tsx`
   - `document-viewer.tsx` (对比现有功能)

2. **工具展示**
   - `tool-ui/audio.tsx`
   - `tool-ui/display-image.tsx`
   - `tool-ui/link-preview.tsx`
   - `tool-ui/scrape-webpage.tsx`

3. **UI 增强**
   - `ui/bento-grid.tsx`
   - `ui/spotlight.tsx`
   - `ui/tilt.tsx`
   - `ui/avatar.tsx`
   - `ui/calendar.tsx`

4. **工具组件**
   - `copy-button.tsx`
   - `sidebar/page-usage-display.tsx`

5. **营销和其他组件（全部迁移）**
   - `homepage/` 所有组件（7个）
   - `pricing/pricing-section.tsx`
   - `contact/contact-form.tsx`
   - `sources/GridPattern.tsx`
   - `announcement-banner.tsx`
   - `prompt-kit/*` 所有组件

## 四、迁移策略详细说明

### 策略 1：直接迁移
**适用于：** SurfSense 独有且 Langflow 缺失的组件

**步骤：**
1. 复制组件文件到对应目录
2. 更新导入路径（`@/` 别名）
3. 调整状态管理（Jotai → Zustand）
4. 适配 API 调用（使用 React Query hooks）
5. 添加必要依赖
6. 测试功能完整性

**示例组件：**
- `assistant-ui/thread.tsx`
- `BlockNoteEditor.tsx`
- `settings/model-config-manager.tsx`

### 策略 2：功能增强
**适用于：** Langflow 有类似组件但功能不足

**步骤：**
1. 对比两边组件功能差异
2. 提取 SurfSense 的额外功能
3. 增强 Langflow 现有组件
4. 保持 Langflow 的代码风格
5. 测试兼容性

**示例组件：**
- `dashboard-breadcrumb.tsx` → 增强 Langflow 的面包屑
- `DocumentUploadTab.tsx` → 增强现有文件上传
- `markdown-viewer.tsx` → 增强 react-markdown 使用

### 策略 3：适配集成
**适用于：** 需要适配 Langflow 架构的组件

**步骤：**
1. 分析组件的核心功能
2. 设计适配层
3. 重写状态管理部分
4. 重写 API 调用部分
5. 保留 UI 逻辑
6. 集成测试

**示例组件：**
- `TokenHandler.tsx` → 适配 Langflow 认证系统
- `I18nProvider.tsx` → 适配 Langflow i18n 系统

### 策略 4：重新实现
**适用于：** 功能简单但实现方式不同的组件

**步骤：**
1. 理解 SurfSense 组件需求
2. 基于 Langflow 组件库重新实现
3. 保持相同的 API 接口
4. 测试功能等价性

**示例组件：**
- `copy-button.tsx` → 基于 Langflow Button 实现
- `sidebar/page-usage-display.tsx` → 基于 Langflow UI 组件实现

## 五、状态管理迁移方案

### Jotai → Zustand 迁移模式

**SurfSense 模式（Jotai）：**
```typescript
// atoms/searchSpaceAtom.ts
import { atom } from 'jotai';
export const searchSpaceAtom = atom<SearchSpace | null>(null);

// 组件中使用
import { useAtom } from 'jotai';
const [searchSpace, setSearchSpace] = useAtom(searchSpaceAtom);
```

**Langflow 模式（Zustand）：**
```typescript
// stores/searchSpaceStore.ts
import { create } from 'zustand';

interface SearchSpaceStore {
  searchSpace: SearchSpace | null;
  setSearchSpace: (space: SearchSpace | null) => void;
}

export const useSearchSpaceStore = create<SearchSpaceStore>((set) => ({
  searchSpace: null,
  setSearchSpace: (searchSpace) => set({ searchSpace }),
}));

// 组件中使用
const { searchSpace, setSearchSpace } = useSearchSpaceStore();
```

**迁移清单：**
- [ ] `atoms/searchSpaceAtom.ts` → `stores/spacesStore.ts` (已存在)
- [ ] `atoms/userAtom.ts` → `stores/userStore.ts` (检查是否存在)
- [ ] `atoms/llmConfigAtom.ts` → 集成到现有 store
- [ ] `atoms/chatAtom.ts` → `stores/chatStore.ts` (已创建)
- [ ] `atoms/documentAtom.ts` → `stores/documentsStore.ts` (已存在)
- [ ] `atoms/connectorAtom.ts` → `stores/connectorsStore.ts` (已存在)

## 六、API 调用适配方案

### SurfSense → Langflow API 映射

**SurfSense 模式：**
```typescript
// 使用 fetch + jotai-tanstack-query
import { useQuery } from 'jotai-tanstack-query';
const { data } = useQuery({
  queryKey: ['searchSpaces'],
  queryFn: () => fetch('/api/search-spaces').then(r => r.json())
});
```

**Langflow 模式：**
```typescript
// 使用 React Query hooks
import { useGetSpacesQuery } from '@/controllers/API/queries/spaces';
const { data } = useGetSpacesQuery({});
```

**适配策略：**
1. 将所有 API 调用替换为已创建的 React Query hooks
2. 使用 `@/controllers/API/queries/*` 中的 hooks
3. 保持组件逻辑不变
4. 更新类型定义使用 `@/types/api`

## 七、样式系统兼容性

### Tailwind CSS 版本处理

**问题：**
- SurfSense 使用 Tailwind v4 (major changes)
- Langflow 使用 Tailwind v3

**解决方案：**
1. **保持 Langflow Tailwind v3**
2. **转换 v4 特有语法到 v3**
3. **避免使用 v4 新特性**

**需要转换的语法示例：**
```css
/* Tailwind v4 (SurfSense) */
@theme {
  --color-primary: #000;
}

/* Tailwind v3 (Langflow) - 保持现有方式 */
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#000'
      }
    }
  }
}
```

## 八、实施路线图（基于用户确认的策略）

### 阶段 1：依赖准备（Day 1）

**目标：** 一次性安装所有必需依赖

#### 必需依赖安装清单

```bash
# 安装核心依赖
npm install @assistant-ui/react@^0.11.53 \
  @assistant-ui/react-markdown@^0.11.9 \
  @blocknote/core@^0.45.0 \
  @blocknote/mantine@^0.45.0 \
  @blocknote/react@^0.45.0 \
  @radix-ui/react-avatar@^1.1.10 \
  @radix-ui/react-toggle@^1.1.9 \
  @radix-ui/react-toggle-group@^1.1.10 \
  sonner@^2.0.6 \
  react-day-picker@^9.8.1 \
  react-dropzone@^14.3.8 \
  @tanstack/react-table@^8.21.3 \
  @number-flow/react@^0.5.10 \
  canvas-confetti@^1.9.3 \
  motion@^12.23.22 \
  emblor@^1.4.8 \
  streamdown@^1.6.10 \
  react-json-view-lite@^2.4.1
```

#### 选择性升级现有依赖

```bash
# 低风险升级
npm install @tanstack/react-query@^5.90.7 \
  @tanstack/react-query-devtools@^5.90.2 \
  zustand@^5.0.9 \
  tailwind-merge@^3.3.1
```

**任务清单：**
- [ ] 执行依赖安装命令
- [ ] 更新 package.json
- [ ] 运行 `npm install` 确保无冲突
- [ ] 测试 Langflow 现有功能无回归
- [ ] 创建迁移工作分支 `feature/surfsense-components-migration`

### 阶段 2：UI 基础组件迁移（Day 2-3）

**目标：** 仅迁移 Langflow 缺失的 UI 组件

#### 2.1 新增 UI 组件列表

迁移到 `/Users/jiangwei/Python/langflow/src/frontend/src/components/ui/`

| 组件文件 | 源路径 | 目标路径 | 说明 |
|---------|--------|---------|------|
| `avatar.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 用户头像组件 |
| `calendar.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 日期选择器 |
| `sonner.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | Toast 通知 |
| `bento-grid.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 网格布局 |
| `spotlight.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 聚光灯效果 |
| `tilt.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 3D 倾斜效果 |
| `toggle.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 切换控件 |
| `toggle-group.tsx` | SurfSense/components/ui/ | Langflow/components/ui/ | 切换组控件 |

**迁移步骤：**
1. 复制组件文件到目标目录
2. 更新导入路径（`@/` 别名）
3. 确保与 Langflow Tailwind 配置兼容
4. 测试组件渲染
5. 更新 `components/ui/index.ts` 导出

#### 2.2 验证现有 UI 组件

确认以下组件无需迁移（Langflow 已有）：
- ✅ button, input, textarea, checkbox, select, switch, label, form
- ✅ card, separator, accordion, collapsible, tabs, sidebar
- ✅ alert, alert-dialog, dialog, tooltip, dropdown-menu
- ✅ table, badge, progress, skeleton, popover, scroll-area

### 阶段 3：Provider 组件迁移（Day 4）

**目标：** 迁移状态管理和上下文提供者

#### 3.1 状态管理转换

**Jotai → Zustand 转换规则：**

**示例转换：**
```typescript
// SurfSense (Jotai)
// atoms/searchSpaceAtom.ts
import { atom } from 'jotai';
export const searchSpaceAtom = atom<SearchSpace | null>(null);

// Langflow (Zustand)
// stores/spacesStore.ts (已存在，无需创建)
import { create } from 'zustand';
interface SpacesStore {
  currentSpace: SearchSpace | null;
  setCurrentSpace: (space: SearchSpace | null) => void;
}
export const useSpacesStore = create<SpacesStore>((set) => ({
  currentSpace: null,
  setCurrentSpace: (currentSpace) => set({ currentSpace }),
}));
```

**需要转换的 Atoms：**
- [ ] `atoms/userAtom.ts` → 集成到现有 `stores/authStore.ts` 或创建新 store
- [ ] `atoms/llmConfigAtom.ts` → 创建 `stores/llmConfigStore.ts`
- [ ] `atoms/chatAtom.ts` → 已有 `stores/chatStore.ts`，验证功能
- [ ] 其他自定义 atoms → 根据功能创建对应 store

#### 3.2 Provider 组件迁移

**I18nProvider 适配：**

| 文件 | 源路径 | 策略 |
|------|--------|------|
| `I18nProvider.tsx` | SurfSense/components/providers/ | 适配到 Langflow i18n 系统 |

**步骤：**
1. 分析 SurfSense I18nProvider 实现
2. 对比 Langflow 现有 i18n 系统
3. 适配或增强 Langflow i18n
4. 确保 next-intl 功能可用（或使用 Langflow i18n）

#### 3.3 Theme Provider

SurfSense 使用 next-themes，Langflow 已有主题系统：
- [ ] 验证 Langflow 主题系统兼容性
- [ ] 无需迁移 SurfSense theme-provider（使用 Langflow 现有）

### 阶段 4：核心业务组件迁移（Day 5-10）

**目标：** 迁移所有业务逻辑组件

#### 4.1 AI 聊天组件（优先级最高）

迁移到 `/Users/jiangwei/Python/langflow/src/frontend/src/components/`

创建新目录：`components/assistant-ui/`

| 组件 | 行数 | 迁移任务 |
|------|------|---------|
| `thread.tsx` | 1092 | 1. 完整复制<br>2. 转换 Jotai → Zustand<br>3. 适配 API 调用<br>4. 测试流式响应 |
| `thread-list.tsx` | - | 同上 |
| `attachment.tsx` | - | 1. 复制组件<br>2. 适配文件上传 API |
| `inline-citation.tsx` | - | 1. 复制组件<br>2. 适配引用数据结构 |
| `markdown-text.tsx` | - | 1. 对比 Langflow react-markdown 使用<br>2. 合并或替换 |
| `tool-fallback.tsx` | - | 直接复制 |
| `tooltip-icon-button.tsx` | - | 使用 Langflow 现有 tooltip + button |

**关键适配点：**
- **状态管理**：将所有 `useAtom(chatAtom)` 替换为 `useChatStore()`
- **API 调用**：使用 Langflow React Query hooks
- **类型定义**：使用 `@/types/api` 中的类型

#### 4.2 富文本编辑器组件

迁移到 `components/`

| 组件 | 迁移任务 |
|------|---------|
| `BlockNoteEditor.tsx` | 1. 完整复制<br>2. 适配主题系统<br>3. 测试所有编辑功能 |
| `DynamicBlockNoteEditor.tsx` | 1. 复制<br>2. 测试动态加载 |

#### 4.3 设置管理组件

创建目录：`components/settings/`

| 组件 | 行数 | 迁移任务 |
|------|------|---------|
| `model-config-manager.tsx` | 500 | 1. 复制组件<br>2. 转换状态管理<br>3. 适配 LLM Configs API hooks<br>4. 测试 CRUD 操作 |
| `llm-role-manager.tsx` | - | 同上 |
| `prompt-config-manager.tsx` | - | 同上 |

#### 4.4 聊天功能组件

创建目录：`components/new-chat/`

| 组件 | 行数 | 迁移任务 |
|------|------|---------|
| `model-selector.tsx` | 388 | 1. 复制组件<br>2. 适配 LLM configs store<br>3. 测试模型切换 |
| `chat-header.tsx` | - | 1. 复制<br>2. 适配导航逻辑 |
| `model-config-sidebar.tsx` | - | 1. 复制<br>2. 集成到侧边栏系统 |
| `DocumentsDataTable.tsx` | - | 1. 基于 Langflow table 组件实现<br>2. 适配文档 API |
| `source-detail-panel.tsx` | - | 1. 复制<br>2. 适配数据源 API |

#### 4.5 侧边栏组件

创建目录：`components/sidebar/`（或增强现有 sidebarComponent）

| 组件 | 迁移任务 |
|------|---------|
| `app-sidebar.tsx` (474行) | 1. 对比 Langflow sidebarComponent<br>2. 合并功能或替换<br>3. 适配导航逻辑 |
| `nav-chats.tsx` | 直接迁移 |
| `nav-notes.tsx` | 直接迁移 |
| `nav-main.tsx` | 对比现有，选择性合并 |
| `nav-secondary.tsx` | 对比现有，选择性合并 |
| `all-chats-sidebar.tsx` | 直接迁移 |
| `all-notes-sidebar.tsx` | 直接迁移 |
| `page-usage-display.tsx` | 直接迁移 |
| `AppSidebarProvider.tsx` | 转换为 Zustand store |

#### 4.6 数据源组件

创建目录：`components/sources/`

| 组件 | 迁移任务 |
|------|---------|
| `ConnectorsTab.tsx` (204行) | 1. 复制<br>2. 适配 connectors API<br>3. 测试连接器展示 |
| `DocumentUploadTab.tsx` | 1. 对比 Langflow 文件上传<br>2. 增强现有功能 |
| `YouTubeTab.tsx` | 直接迁移 |
| `GridPattern.tsx` | 直接迁移（装饰性组件） |
| `connector-data.tsx` | 直接迁移（配置数据） |

#### 4.7 连接器编辑组件

创建目录：`components/editConnector/`

| 组件 | 迁移任务 |
|------|---------|
| `EditConnectorNameForm.tsx` | 1. 复制<br>2. 适配 connectors API |
| `EditGitHubConnectorConfig.tsx` | 同上 |
| `EditSimpleTokenForm.tsx` | 同上 |
| `EditConnectorLoadingSkeleton.tsx` | 使用 Langflow skeleton 组件 |
| `types.ts` | 对比 `@/types/api/connectors.ts` |

#### 4.8 工具 UI 组件

创建目录：`components/tool-ui/`

| 组件/目录 | 迁移任务 |
|----------|---------|
| `article/` | 直接迁移 |
| `audio.tsx` | 直接迁移 |
| `deepagent-thinking.tsx` | 直接迁移（核心功能） |
| `display-image.tsx` | 对比 Langflow ImageViewer |
| `generate-podcast.tsx` | 直接迁移 |
| `image/` | 对比 Langflow ImageViewer，选择性合并 |
| `link-preview.tsx` | 直接迁移 |
| `media-card/` | 直接迁移 |
| `scrape-webpage.tsx` | 直接迁移 |

#### 4.9 根目录组件

迁移到 `components/`

| 组件 | 迁移任务 |
|------|---------|
| `LanguageSwitcher.tsx` | 1. 适配 Langflow i18n<br>2. 或直接迁移 |
| `UserDropdown.tsx` | 对比 Langflow 现有用户菜单 |
| `copy-button.tsx` | 基于 Langflow Button 实现 |
| `dashboard-breadcrumb.tsx` (280行) | 1. 对比 Langflow breadcrumb<br>2. 增强功能 |
| `document-viewer.tsx` | 对比现有 viewer 组件 |
| `inference-params-editor.tsx` | 直接迁移 |
| `json-metadata-viewer.tsx` | 对比 Langflow JSON viewer |
| `markdown-viewer.tsx` | 对比 Langflow react-markdown 使用 |
| `search-space-form.tsx` | 1. 直接迁移<br>2. 适配 spaces API |
| `announcement-banner.tsx` | 直接迁移（必须迁移） |

#### 4.10 首页和营销组件

创建目录：`components/homepage/`, `components/pricing/`, `components/contact/`

| 目录/组件 | 数量 | 迁移策略 |
|----------|------|---------|
| `homepage/*` | 7 | 全部迁移，后续决定保留 |
| `pricing/*` | 1 | 全部迁移 |
| `contact/*` | 1 | 全部迁移 |
| `prompt-kit/*` | 1 | 直接迁移 |

### 阶段 5：测试与优化（Day 11-14）

**目标：** 确保所有迁移组件功能正常

#### 5.1 功能测试清单

- [ ] UI 组件渲染测试
  - [ ] 所有新增 UI 组件在明暗主题下正常显示
  - [ ] 响应式设计正常工作
  - [ ] 无样式冲突

- [ ] 聊天功能测试
  - [ ] Thread 组件流式响应正常
  - [ ] 附件上传和显示正常
  - [ ] 引用功能正常
  - [ ] 模型切换正常

- [ ] 编辑器测试
  - [ ] BlockNote 编辑器所有功能正常
  - [ ] 主题切换正常
  - [ ] 保存和加载正常

- [ ] 设置管理测试
  - [ ] LLM 配置 CRUD 正常
  - [ ] 角色管理正常
  - [ ] 提示词配置正常

- [ ] 数据源测试
  - [ ] 连接器展示和管理正常
  - [ ] 文档上传正常
  - [ ] YouTube 集成正常

- [ ] 状态管理测试
  - [ ] 所有 Zustand stores 工作正常
  - [ ] 无状态丢失或不一致
  - [ ] React Query 缓存正常

#### 5.2 性能优化

- [ ] 代码分割和懒加载
  - [ ] 大组件使用 React.lazy
  - [ ] 路由级别代码分割

- [ ] 打包优化
  - [ ] 分析打包大小
  - [ ] 移除未使用的依赖
  - [ ] Tree-shaking 优化

- [ ] 运行时优化
  - [ ] 使用 React.memo 优化重渲染
  - [ ] useMemo/useCallback 优化计算
  - [ ] 虚拟滚动优化长列表

#### 5.3 代码质量

- [ ] TypeScript 无错误
- [ ] ESLint 通过（运行 `make lint`）
- [ ] 代码格式化（运行 `make format_frontend`）
- [ ] 组件 Props 类型完整
- [ ] 无 any 类型滥用

### 阶段 6：文档和交付（Day 15）

**目标：** 完成迁移文档

#### 6.1 迁移文档

创建 `MIGRATION_REPORT.md` 包含：
- 迁移的组件清单
- 新增的依赖列表
- 状态管理转换说明
- API 适配说明
- 已知问题和限制

#### 6.2 使用文档

为新组件创建使用示例：
- AI 聊天组件使用指南
- BlockNote 编辑器集成指南
- 设置管理组件使用
- 数据源组件使用

#### 6.3 交付清单

- [ ] 所有组件迁移完成
- [ ] 功能测试通过
- [ ] 性能测试通过
- [ ] 代码质量检查通过
- [ ] 文档编写完成
- [ ] 创建 Pull Request
- [ ] 代码审查

## 九、风险与缓解措施

### 高风险项

1. **React 版本兼容性**
   - **风险：** SurfSense 使用 React 19，Langflow 使用 React 18
   - **缓解：** 保持 Langflow React 18，测试所有迁移组件兼容性

2. **@assistant-ui 依赖冲突**
   - **风险：** 可能与 Langflow 现有库冲突
   - **缓解：** 在隔离环境中测试，逐步集成

3. **状态管理迁移**
   - **风险：** Jotai → Zustand 可能导致状态丢失
   - **缓解：** 仔细映射所有 atom → store，全面测试

### 中等风险项

1. **样式冲突**
   - **风险：** Tailwind 版本差异导致样式问题
   - **缓解：** 逐组件测试，建立样式转换规则

2. **依赖包体积**
   - **风险：** 新增依赖增加打包大小
   - **缓解：** 使用动态导入，tree-shaking 优化

3. **API 适配**
   - **风险：** API 结构不匹配
   - **缓解：** 建立适配层，保持组件解耦

## 十、成功标准

### 功能完整性
- [ ] 所有 P0 组件功能正常
- [ ] 所有 P1 组件功能正常
- [ ] 状态管理正确迁移
- [ ] API 调用正常工作

### 代码质量
- [ ] TypeScript 无错误
- [ ] ESLint 通过
- [ ] 组件测试覆盖率 > 80%
- [ ] 性能指标无回归

### 用户体验
- [ ] UI 一致性保持
- [ ] 响应式设计正常
- [ ] 暗色模式支持
- [ ] 国际化支持

## 关键文件清单

### 迁移源目录
- `/Users/jiangwei/Python/SurfSense/surfsense_web/components/` - 所有 SurfSense 组件
- `/Users/jiangwei/Python/SurfSense/surfsense_web/package.json` - 依赖参考
- `/Users/jiangwei/Python/SurfSense/surfsense_web/atoms/` - 状态管理 atoms

### 迁移目标目录
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/` - 组件目标目录
- `/Users/jiangwei/Python/langflow/src/frontend/src/stores/` - 状态管理目标目录
- `/Users/jiangwei/Python/langflow/package.json` - 需要更新依赖
- `/Users/jiangwei/Python/langflow/src/frontend/src/types/api/` - 类型定义目录

### 关键配置文件
- `/Users/jiangwei/Python/langflow/tailwind.config.js` - Tailwind 配置
- `/Users/jiangwei/Python/langflow/tsconfig.json` - TypeScript 配置
- `/Users/jiangwei/Python/langflow/src/frontend/src/i18n.ts` - 国际化配置

## 下一步行动

根据本计划，下一步立即执行：

1. **开始阶段 1**：安装所有必需依赖
2. **创建迁移分支**：`feature/surfsense-components-migration`
3. **按顺序执行迁移**：UI 组件 → Provider → 业务组件
4. **每完成一个阶段进行测试**

用户确认开始执行后，按照阶段 1 开始迁移工作。

---

# Yuxi-Know 知识图谱前端迁移计划

**日期：** 2026-01-08
**状态：** 计划阶段
**后端状态：** ✅ 80% 完成（Entity/Relation 模型、CRUD API、图谱 API）
**前端状态：** 🔜 准备开始

## 执行摘要

本计划概述了将 Yuxi-Know 的 Vue 3 + AntV G6 知识图谱可视化前端迁移到 Langflow 的 React 18 + ReactFlow 架构。后端迁移已完成，提供了 Entity 和 Relation 模型以及图谱遍历 API。此前端迁移将把知识图谱可视化直接集成到 Langflow 仪表板中，作为 Space 详情页面的新"Graph"标签页。

**时间估算：** 6-8 周
**复杂度：** 高（图谱可视化、复杂状态管理、性能优化）

## 迁移概览

### 源系统（Yuxi-Know）详细分析

**框架与库：**
- Vue 3.5.21 with Composition API
- AntV G6 v5.0.49（Canvas 渲染引擎）
- Ant Design Vue 4.2.6（UI 组件库）
- D3 v7.9.0（用于力导向布局）

**状态管理架构：**
- **主要方式**：`useGraph` Composable（~/composables/useGraph.js）
- **不使用** Pinia store（graphStore.js 是 Sigma.js 遗留代码）
- 响应式状态：graphData (nodes/edges), selectedItem, showDetailDrawer

**图谱配置详情（GraphCanvas.vue）：**
```javascript
// G6 完整配置
{
  container: containerRef,
  layout: {
    type: 'd3-force',           // 力导向布局
    preventOverlap: true,
    iterations: 150,
    force: {
      center: { x: 0.5, y: 0.5, strength: 0.1 },
      charge: { strength: -400, distanceMax: 600 },
      link: { distance: 100, strength: 0.8 }
    },
    collide: { radius: 40, strength: 0.8, iterations: 3 }
  },
  node: {
    type: 'circle',
    style: {
      size: (d) => Math.min(15 + d.data.degree * 5, 50),  // 15-50px 动态大小
      labelText: (d) => d.data.label,
      opacity: 0.9,
      stroke: getCSSVariable('--color-bg-container'),
      lineWidth: 1.5
    },
    palette: {
      field: 'label',
      color: ['#60a5fa', '#34d399', '#f59e0b', ...]  // 10种颜色
    }
  },
  edge: {
    type: 'quadratic',          // 曲线边
    style: {
      labelText: (d) => d.data.label,
      labelBackground: true,
      endArrow: true,             // 方向箭头
      opacity: 0.8
    }
  },
  behaviors: [
    'drag-element',               // 拖拽节点
    'zoom-canvas',                // 滚轮缩放
    'drag-canvas',                // 平移画布
    'hover-activate',             // 悬停高亮
    {
      type: 'click-select',
      degree: 1,                  // 高亮 1 跳邻居
      multiple: true,
      trigger: ['shift']          // Shift 多选
    }
  ]
}
```

**核心功能实现：**
1. **搜索功能**：通过 `node_label` 参数过滤（'*' 表示全部）
2. **关键词高亮**：监听 `highlightKeywords` prop，应用 'highlighted' 状态
3. **Focus Neighbor**：使用 `setElementState` 隐藏非相关节点/边
4. **度计算**：前端计算节点 degree，用于动态调整节点大小
5. **主题支持**：读取 CSS 变量，监听主题变化重新渲染

**数据流：**
```
API Response
  └─> useGraph.updateGraphData(nodes, edges)
      └─> graphData.nodes/edges (响应式)
          └─> GraphCanvas props
              └─> formatData() 转换为 G6 格式
                  └─> graphInstance.setData()
                      └─> render()
```

### 目标系统（Langflow）
- **框架：** React 18.3.1 with TypeScript
- **图谱库：** @xyflow/react v12.3.6（已安装）
- **状态管理：** Zustand v5.0.9
- **API 层：** React Query v5.90.7
- **UI 组件：** shadcn/ui + Tailwind CSS
- **参考：** LineageGraph 组件（modals/lineageModal/）

### G6 → ReactFlow 关键差异与迁移策略

| 特性 | G6 (Yuxi-Know) | ReactFlow (Langflow) | 迁移方案 |
|------|----------------|----------------------|----------|
| **渲染引擎** | Canvas/WebGL | SVG + HTML | 接受范式差异，利用 SVG 优势 |
| **节点定义** | 数据对象 + 样式函数 | React 组件 | 创建 EntityNode 组件 |
| **布局** | 内置 d3-force | 需外部库 | 使用 dagre 或 d3-force |
| **位置** | 自动计算 | 必须显式提供 x,y | 布局算法计算后赋值 |
| **事件** | `graph.on('node:click')` | `onNodeClick` prop | 直接 React 事件 |
| **状态管理** | 手动 `setElementState` | React state + Zustand | 通过 useState/Zustand 过滤 |
| **样式** | 样式函数 | CSS + inline styles | Tailwind + 动态 className |
| **度计算** | 前端遍历边 | 前端遍历边 | 复用相同逻辑 |

### 核心迁移任务

#### 1. 数据转换（G6 → ReactFlow）

**源数据格式（G6）：**
```javascript
{
  nodes: [
    {
      id: 'node_1',
      data: {
        label: 'Entity Name',
        degree: 5,
        original: { /* API 数据 */ }
      }
    }
  ],
  edges: [
    {
      id: 'edge_1',
      source: 'node_1',
      target: 'node_2',
      data: {
        label: 'relation_type',
        original: { /* API 数据 */ }
      }
    }
  ]
}
```

**目标格式（ReactFlow）：**
```typescript
{
  nodes: [
    {
      id: 'node_1',
      type: 'entityNode',
      position: { x: 100, y: 200 },  // 必须！由布局算法计算
      data: {
        label: 'Entity Name',
        degree: 5,
        original: { /* API 数据 */ }
      }
    }
  ],
  edges: [
    {
      id: 'edge_1',
      source: 'node_1',
      target: 'node_2',
      type: 'relationEdge',
      data: {
        label: 'relation_type',
        original: { /* API 数据 */ }
      },
      markerEnd: { type: MarkerType.ArrowClosed }  // 箭头
    }
  ]
}
```

**转换函数（graphTransform.ts）：**
```typescript
import dagre from 'dagre'

// 1. 计算度
export function calculateDegrees(nodes: Entity[], edges: Relation[]): Map<string, number> {
  const degrees = new Map<string, number>()
  nodes.forEach(n => degrees.set(String(n.id), 0))
  edges.forEach(e => {
    const source = String(e.source_entity_id)
    const target = String(e.target_entity_id)
    degrees.set(source, (degrees.get(source) || 0) + 1)
    degrees.set(target, (degrees.get(target) || 0) + 1)
  })
  return degrees
}

// 2. Entity → GraphNode（无位置）
export function transformEntitiesToNodes(entities: Entity[]): GraphNode[] {
  const degrees = calculateDegrees(entities, [])
  return entities.map(entity => ({
    id: String(entity.id),
    type: 'entityNode',
    position: { x: 0, y: 0 },  // 临时位置
    data: {
      label: entity.name,
      degree: degrees.get(String(entity.id)) || 0,
      entityType: entity.entity_type,
      original: entity
    }
  }))
}

// 3. Relation → GraphEdge
export function transformRelationsToEdges(relations: Relation[]): GraphEdge[] {
  return relations.map((rel, idx) => ({
    id: rel.id ? String(rel.id) : `edge-${idx}`,
    source: String(rel.source_entity_id),
    target: String(rel.target_entity_id),
    type: 'relationEdge',
    data: {
      label: rel.relation_type,
      weight: rel.weight || 1,
      original: rel
    },
    markerEnd: { type: MarkerType.ArrowClosed }
  }))
}

// 4. 应用 Dagre 布局（计算位置）
export function applyDagreLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  direction: 'TB' | 'LR' = 'TB'
): GraphNode[] {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 150 })

  // 节点大小基于 degree
  nodes.forEach(node => {
    const size = Math.min(15 + (node.data.degree || 0) * 5, 50)
    dagreGraph.setNode(node.id, { width: size * 3, height: size * 3 })
  })

  edges.forEach(edge => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  return nodes.map(node => {
    const { x, y } = dagreGraph.node(node.id)
    return {
      ...node,
      position: { x, y }
    }
  })
}

// 5. 实体类型颜色映射（复用 G6 调色板）
export function getEntityTypeColor(entityType: string): string {
  const colorPalette = [
    '#60a5fa', '#34d399', '#f59e0b', '#f472b6', '#22d3ee',
    '#a78bfa', '#f97316', '#4ade80', '#f43f5e', '#2dd4bf'
  ]

  const typeIndex = entityType.charCodeAt(0) % colorPalette.length
  return colorPalette[typeIndex]
}
```

#### 2. 自定义节点组件（EntityNode.tsx）

```typescript
import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { Badge } from '@/components/ui/badge'
import { getEntityTypeColor } from '@/utils/graphTransform'

interface EntityNodeData {
  label: string
  degree: number
  entityType: string
  original: Entity
}

export const EntityNode = memo(({ data, selected }: NodeProps<EntityNodeData>) => {
  const { label, degree, entityType } = data

  // 动态大小（复用 G6 公式）
  const size = Math.min(15 + degree * 5, 50)
  const color = getEntityTypeColor(entityType)

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />

      <div
        className={`
          rounded-full flex items-center justify-center border-4
          transition-all shadow-md
          ${selected ? 'ring-4 ring-blue-500 ring-opacity-50' : ''}
        `}
        style={{
          width: size,
          height: size,
          backgroundColor: color,
          borderColor: selected ? '#3b82f6' : color,
        }}
      >
        {/* 节点内容（可选，小节点时隐藏） */}
        {size > 30 && (
          <div className="text-white text-xs font-bold truncate max-w-[40px]">
            {label.charAt(0)}
          </div>
        )}
      </div>

      {/* 节点下方标签 */}
      <div className="absolute top-full mt-2 text-xs text-center">
        <div className="font-medium text-gray-900 dark:text-gray-100 max-w-[120px] truncate">
          {label}
        </div>
        <Badge variant="secondary" className="mt-1 text-xs">
          {entityType}
        </Badge>
      </div>

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </>
  )
})

EntityNode.displayName = 'EntityNode'
```

#### 3. 自定义边组件（RelationEdge.tsx）

```typescript
import { memo } from 'react'
import { EdgeProps, getBezierPath, EdgeLabelRenderer, MarkerType } from '@xyflow/react'

interface RelationEdgeData {
  label: string
  weight: number
  original: Relation
}

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
}: EdgeProps<RelationEdgeData>) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  const { label, weight } = data || {}
  const strokeWidth = 1.2 + (weight || 1) * 0.5  // 基于权重调整宽度

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        strokeWidth={strokeWidth}
        stroke={selected ? '#3b82f6' : '#9ca3af'}
        fill="none"
        opacity={0.8}
      />

      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <div className="bg-white dark:bg-gray-800 px-2 py-1 rounded text-xs border border-gray-200 dark:border-gray-700 shadow-sm">
            {label}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  )
})

RelationEdge.displayName = 'RelationEdge'
```

#### 4. Focus Neighbor 实现（复用 G6 逻辑）

```typescript
// 在 GraphCanvas.tsx 或 useGraph.ts
const focusNode = useCallback((nodeId: string) => {
  if (!nodes || !edges) return

  // 找到邻居节点
  const neighborIds = new Set<string>()
  const relatedEdgeIds = new Set<string>()

  edges.forEach(edge => {
    if (edge.source === nodeId) {
      neighborIds.add(edge.target)
      relatedEdgeIds.add(edge.id)
    } else if (edge.target === nodeId) {
      neighborIds.add(edge.source)
      relatedEdgeIds.add(edge.id)
    }
  })

  // 过滤节点和边
  const focusedNodes = nodes.filter(node =>
    node.id === nodeId || neighborIds.has(node.id)
  )

  const focusedEdges = edges.filter(edge =>
    relatedEdgeIds.has(edge.id)
  )

  setNodes(focusedNodes)
  setEdges(focusedEdges)
  setIsFocused(true)
}, [nodes, edges])

const clearFocus = useCallback(() => {
  if (originalNodes && originalEdges) {
    setNodes(originalNodes)
    setEdges(originalEdges)
    setIsFocused(false)
  }
}, [originalNodes, originalEdges])
```

#### 5. 关键词高亮（复用 G6 逻辑）

```typescript
// 在 GraphCanvas.tsx
const highlightKeywords = (keywords: string[]) => {
  if (!keywords || keywords.length === 0) return

  const updatedNodes = nodes.map(node => {
    const shouldHighlight = keywords.some(keyword =>
      keyword.trim() !== '' &&
      node.data.label.toLowerCase().includes(keyword.toLowerCase())
    )

    return {
      ...node,
      className: shouldHighlight ? 'highlighted-node' : ''
    }
  })

  setNodes(updatedNodes)
}

// CSS
.highlighted-node {
  animation: highlightPulse 2s infinite ease-in-out;
}

@keyframes highlightPulse {
  0% { filter: brightness(1); }
  50% { filter: brightness(1.3) drop-shadow(0 0 8px rgba(255, 0, 0, 0.8)); }
  100% { filter: brightness(1); }
}
```

## 关键文件路径

### 源文件（Yuxi-Know Vue）

**核心组件：**
- `/Users/jiangwei/Python/Yuxi-Know/web/src/components/GraphCanvas.vue` (450行) - 主图谱画布
- `/Users/jiangwei/Python/Yuxi-Know/web/src/components/GraphDetailPanel.vue` - 详情面板
- `/Users/jiangwei/Python/Yuxi-Know/web/src/components/KnowledgeGraphSection.vue` - 图谱区域组件
- `/Users/jiangwei/Python/Yuxi-Know/web/src/views/GraphView.vue` - 独立图谱视图页面

**状态管理：**
- `/Users/jiangwei/Python/Yuxi-Know/web/src/composables/useGraph.js` - Graph composable（主要状态管理）
- `/Users/jiangwei/Python/Yuxi-Know/web/src/stores/graphStore.js` - Sigma.js store（遗留代码，未使用）

**API 集成：**
- `/Users/jiangwei/Python/Yuxi-Know/web/src/apis/graph_api.js` - 统一图谱 API

**依赖配置：**
- `/Users/jiangwei/Python/Yuxi-Know/web/package.json` - @antv/g6 v5.0.49, graphology, d3

### 目标文件（Langflow React）

**主页面和组件：**
- `/Users/jiangwei/Python/langflow/src/frontend/src/pages/SpaceDetailPage/GraphPage.tsx` - 主图谱页面
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/GraphCanvas.tsx` - ReactFlow 画布
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/GraphDetailPanel.tsx` - 详情面板
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/GraphControls.tsx` - 控制组件
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/GraphSearchBar.tsx` - 搜索栏
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/GraphLegend.tsx` - 图例
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/nodes/EntityNode.tsx` - 自定义节点
- `/Users/jiangwei/Python/langflow/src/frontend/src/components/knowledge-graph/nodes/RelationEdge.tsx` - 自定义边

**状态管理：**
- `/Users/jiangwei/Python/langflow/src/frontend/src/stores/graphStore.ts` - Zustand graph store
- `/Users/jiangwei/Python/langflow/src/frontend/src/hooks/useGraph.ts` - Graph hook

**API 层：**
- `/Users/jiangwei/Python/langflow/src/frontend/src/controllers/API/queries/graphs/use-get-subgraph.ts`
- `/Users/jiangwei/Python/langflow/src/frontend/src/controllers/API/queries/graphs/use-get-neighbors.ts`
- `/Users/jiangwei/Python/langflow/src/frontend/src/controllers/API/queries/graphs/use-get-stats.ts`

**工具函数：**
- `/Users/jiangwei/Python/langflow/src/frontend/src/utils/graphTransform.ts` - 数据转换和布局

**类型定义：**
- `/Users/jiangwei/Python/langflow/src/frontend/src/types/api/graphs.ts` - Graph 类型

### 后端 API 参考（已完成）
- `/Users/jiangwei/Python/langflow/src/backend/base/langflow/api/v1/entities.py` - Entity CRUD
- `/Users/jiangwei/Python/langflow/src/backend/base/langflow/api/v1/graphs.py` - Graph 查询
- `/Users/jiangwei/Python/langflow/src/backend/base/langflow/services/database/models/entity/crud.py` - Entity CRUD 实现
- `/Users/jiangwei/Python/langflow/src/backend/base/langflow/services/database/models/relation/crud.py` - Relation CRUD 实现（含 BFS 子图遍历）

## Langflow 后端 API 详细分析

### API 架构差异对比

**CRITICAL API 差异：**

| 特性 | Yuxi-Know | Langflow | 迁移影响 |
|------|-----------|----------|---------|
| **获取图谱数据** | GET `/api/graph/subgraph?node_label=*` | POST `/graphs/{space_id}/subgraph` + body | **需要两步流程** |
| **起始节点** | 支持通配符 `*` 获取全部 | 必须提供 `entity_ids: [1,2,3]` | 前端需先调用 list entities |
| **参数位置** | Query parameters | Path + Request body | 更改请求方式 |
| **权限控制** | 无明确权限 | RBAC 权限检查 (`DOCUMENTS_READ`) | 处理 403 错误 |
| **响应格式** | `{ nodes: [...], edges: [...] }` | `{ entities: [...], relations: [...] }` | 字段名不同 |

### 核心 API 端点详解

#### 1. 获取子图数据 - 两步流程

**步骤 1: 获取实体列表（用于初始加载）**

```typescript
// API: GET /entities/?space_id={id}&page=1&page_size=20
interface ListEntitiesRequest {
  space_id: number
  entity_type?: string  // 可选：按类型过滤
  search?: string       // 可选：搜索名称
  page?: number         // 默认 1
  page_size?: number    // 默认 50
}

interface ListEntitiesResponse {
  items: EntityRead[]
  page: number
  page_size: number
  total_count: number
}

interface EntityRead {
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
```

**步骤 2: 获取子图（BFS 遍历）**

```typescript
// API: POST /graphs/{space_id}/subgraph
interface SubgraphRequest {
  entity_ids: number[]  // 起始实体 ID 列表（必需！）
  max_depth: number     // 默认 2，BFS 最大深度
  max_nodes: number     // 默认 100，节点数量限制
}

interface SubgraphResponse {
  entities: EntityRead[]
  relations: RelationRead[]
}

interface RelationRead {
  id: number
  space_id: number
  source_entity_id: number
  target_entity_id: number
  document_id: number | null
  chunk_id: number | null
  relation_type: string
  description: string | null
  weight: number  // 0.0-1.0
  properties: Record<string, any>
  created_at: string
  updated_at: string | null
}
```

**BFS 遍历算法实现（后端 `get_subgraph`）：**

```python
# 位置：relation/crud.py:252-308
async def get_subgraph(
    db: AsyncSession,
    entity_ids: list[int],
    max_depth: int = 2,
    max_nodes: int = 100,
) -> dict:
    visited_entities = set(entity_ids)
    all_relations = []
    current_entities = set(entity_ids)

    # BFS traversal
    for _ in range(max_depth):
        if len(visited_entities) >= max_nodes:
            break

        next_entities = set()

        for entity_id in current_entities:
            # 获取该实体的所有关系（双向）
            relations = await get_relations_by_entity(db, entity_id, direction="both")
            all_relations.extend(relations)

            # 添加连接的实体
            for relation in relations:
                if relation.source_entity_id not in visited_entities:
                    next_entities.add(relation.source_entity_id)
                if relation.target_entity_id not in visited_entities:
                    next_entities.add(relation.target_entity_id)

        visited_entities.update(next_entities)
        current_entities = next_entities

        if not current_entities:
            break

    # 获取所有访问过的实体
    stmt = select(Entity).where(Entity.id.in_(list(visited_entities)[:max_nodes]))
    entities = list(result.all())

    # 去重关系
    unique_relations = {r.id: r for r in all_relations}.values()

    return {"entities": entities, "relations": list(unique_relations)}
```

#### 2. 扩展邻居节点

```typescript
// API: GET /graphs/{space_id}/entity/{entity_id}/relations?direction=both
interface GetNeighborsRequest {
  space_id: number
  entity_id: number
  direction: 'outgoing' | 'incoming' | 'both'  // 默认 'both'
}

interface GetNeighborsResponse {
  entity_id: number
  relations: RelationRead[]
}

// 用途：点击"Expand Neighbors"时调用
// 1. 调用此 API 获取关系
// 2. 提取新的 entity_ids
// 3. 调用 GET /entities/{entity_id} 获取实体详情
// 4. 将新实体和关系添加到图谱
```

#### 3. 搜索实体

```typescript
// API: GET /entities/?space_id={id}&search={query}
interface SearchEntitiesRequest {
  space_id: number
  search: string  // 部分匹配，不区分大小写（ILIKE）
  limit?: number  // 默认 50
}

// 实现：entity/crud.py:114-140
// 使用 SQLAlchemy ilike: Entity.name.ilike(f"%{name_query}%")
// 返回：List[EntityRead]
```

#### 4. 获取图谱统计

```typescript
// API: GET /graphs/{space_id}/stats
interface GraphStatsResponse {
  space_id: number
  entity_count: number
  relation_count: number
  entity_type_distribution: Record<string, number>
  relation_type_distribution: Record<string, number>
}

// 示例响应：
{
  "space_id": 123,
  "entity_count": 450,
  "relation_count": 890,
  "entity_type_distribution": {
    "Person": 120,
    "Organization": 80,
    "Location": 150,
    "Concept": 100
  },
  "relation_type_distribution": {
    "WorksFor": 200,
    "LocatedIn": 150,
    "RelatedTo": 300,
    "PartOf": 240
  }
}
```

### React Query Hooks 实现

#### Hook 1: useGetEntitiesQuery

```typescript
// 文件：src/frontend/src/controllers/API/queries/graphs/use-get-entities.ts

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import { EntityRead, PaginatedResponse } from '@/types/api'

interface GetEntitiesParams {
  space_id: number
  entity_type?: string
  search?: string
  page?: number
  page_size?: number
}

export function useGetEntitiesQuery(params: GetEntitiesParams) {
  return useQuery({
    queryKey: ['entities', params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<EntityRead>>('/entities/', {
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
    enabled: !!params.space_id,
    staleTime: 30000,  // 30 秒缓存
  })
}
```

#### Hook 2: useGetSubgraphQuery

```typescript
// 文件：src/frontend/src/controllers/API/queries/graphs/use-get-subgraph.ts

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import { EntityRead, RelationRead } from '@/types/api'

interface SubgraphRequest {
  entity_ids: number[]
  max_depth?: number
  max_nodes?: number
}

interface SubgraphResponse {
  entities: EntityRead[]
  relations: RelationRead[]
}

export function useGetSubgraphQuery(
  spaceId: number,
  request: SubgraphRequest,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ['subgraph', spaceId, request],
    queryFn: async () => {
      const response = await api.post<SubgraphResponse>(
        `/graphs/${spaceId}/subgraph`,
        {
          entity_ids: request.entity_ids,
          max_depth: request.max_depth || 2,
          max_nodes: request.max_nodes || 100,
        }
      )
      return response.data
    },
    enabled: options?.enabled !== false && request.entity_ids.length > 0,
    staleTime: 60000,  // 1 分钟缓存
  })
}
```

#### Hook 3: useExpandNeighbors (Mutation)

```typescript
// 文件：src/frontend/src/controllers/API/queries/graphs/use-expand-neighbors.ts

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/controllers/API'
import { RelationRead, EntityRead } from '@/types/api'

interface ExpandNeighborsRequest {
  space_id: number
  entity_id: number
  direction?: 'outgoing' | 'incoming' | 'both'
}

interface ExpandNeighborsResponse {
  entity_id: number
  relations: RelationRead[]
}

export function useExpandNeighbors() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: ExpandNeighborsRequest) => {
      // Step 1: 获取关系
      const relationsResponse = await api.get<ExpandNeighborsResponse>(
        `/graphs/${request.space_id}/entity/${request.entity_id}/relations`,
        {
          params: { direction: request.direction || 'both' }
        }
      )

      // Step 2: 提取新实体 ID
      const newEntityIds = new Set<number>()
      relationsResponse.data.relations.forEach(rel => {
        newEntityIds.add(rel.source_entity_id)
        newEntityIds.add(rel.target_entity_id)
      })

      // Step 3: 获取新实体详情
      const entityPromises = Array.from(newEntityIds).map(id =>
        api.get<EntityRead>(`/entities/${id}`)
      )
      const entityResponses = await Promise.all(entityPromises)
      const newEntities = entityResponses.map(res => res.data)

      return {
        newEntities,
        newRelations: relationsResponse.data.relations,
      }
    },
    onSuccess: (data, variables) => {
      // 更新子图缓存
      queryClient.invalidateQueries({
        queryKey: ['subgraph', variables.space_id]
      })
    },
  })
}
```

#### Hook 4: useGetGraphStats

```typescript
// 文件：src/frontend/src/controllers/API/queries/graphs/use-get-graph-stats.ts

import { useQuery } from '@tanstack/react-query'
import { api } from '@/controllers/API'

interface GraphStatsResponse {
  space_id: number
  entity_count: number
  relation_count: number
  entity_type_distribution: Record<string, number>
  relation_type_distribution: Record<string, number>
}

export function useGetGraphStatsQuery(spaceId: number) {
  return useQuery({
    queryKey: ['graph-stats', spaceId],
    queryFn: async () => {
      const response = await api.get<GraphStatsResponse>(
        `/graphs/${spaceId}/stats`
      )
      return response.data
    },
    enabled: !!spaceId,
    staleTime: 120000,  // 2 分钟缓存（统计不常变）
  })
}
```

### 前端数据加载流程

#### 流程 1：初始加载图谱（"显示全部"）

```typescript
// 在 GraphPage.tsx 中实现
export default function GraphPage() {
  const { spaceId } = useParams()
  const [selectedEntityIds, setSelectedEntityIds] = useState<number[]>([])

  // Step 1: 获取前 N 个实体作为起始点
  const { data: entitiesData, isLoading: entitiesLoading } = useGetEntitiesQuery({
    space_id: Number(spaceId),
    page: 1,
    page_size: 20,  // 获取前 20 个实体
  })

  // Step 2: 使用实体 ID 获取子图
  const startingEntityIds = entitiesData?.items.slice(0, 10).map(e => e.id) || []

  const { data: subgraphData, isLoading: subgraphLoading } = useGetSubgraphQuery(
    Number(spaceId),
    {
      entity_ids: startingEntityIds,
      max_depth: 2,
      max_nodes: 100,
    },
    { enabled: startingEntityIds.length > 0 }
  )

  // Step 3: 转换数据为 ReactFlow 格式
  const { nodes, edges } = useMemo(() => {
    if (!subgraphData) return { nodes: [], edges: [] }

    const transformedNodes = transformEntitiesToNodes(subgraphData.entities)
    const transformedEdges = transformRelationsToEdges(subgraphData.relations)

    // 应用布局算法
    const nodesWithLayout = applyDagreLayout(transformedNodes, transformedEdges)

    return { nodes: nodesWithLayout, edges: transformedEdges }
  }, [subgraphData])

  // Loading/Error handling...
  return <GraphCanvas nodes={nodes} edges={edges} />
}
```

#### 流程 2：搜索实体并显示子图

```typescript
// 在 GraphSearchBar.tsx 中实现
export function GraphSearchBar() {
  const { spaceId } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const { setSelectedEntityIds } = useGraphStore()

  // 实时搜索
  const { data: searchResults } = useGetEntitiesQuery({
    space_id: Number(spaceId),
    search: searchQuery,
    page_size: 10,
  })

  const handleSelectEntity = (entity: EntityRead) => {
    // 更新选中实体，触发子图重新加载
    setSelectedEntityIds([entity.id])
  }

  return (
    <Command>
      <CommandInput
        value={searchQuery}
        onValueChange={setSearchQuery}
        placeholder="Search entities..."
      />
      <CommandList>
        {searchResults?.items.map(entity => (
          <CommandItem
            key={entity.id}
            onSelect={() => handleSelectEntity(entity)}
          >
            <span className="font-medium">{entity.name}</span>
            <Badge variant="secondary">{entity.entity_type}</Badge>
          </CommandItem>
        ))}
      </CommandList>
    </Command>
  )
}
```

#### 流程 3：扩展邻居节点

```typescript
// 在 GraphCanvas.tsx 或 GraphDetailPanel.tsx 中实现
export function GraphDetailPanel({ selectedNode }: { selectedNode: GraphNode }) {
  const { spaceId } = useParams()
  const { nodes, edges, addNodes, addEdges } = useGraphStore()
  const expandNeighbors = useExpandNeighbors()

  const handleExpandNeighbors = async () => {
    const entityId = Number(selectedNode.id)

    const result = await expandNeighbors.mutateAsync({
      space_id: Number(spaceId),
      entity_id: entityId,
      direction: 'both',
    })

    // 过滤已存在的节点
    const existingNodeIds = new Set(nodes.map(n => n.id))
    const newNodes = result.newEntities
      .filter(e => !existingNodeIds.has(String(e.id)))
      .map(e => ({
        id: String(e.id),
        type: 'entityNode',
        position: { x: 0, y: 0 },  // 临时位置
        data: {
          label: e.name,
          entityType: e.entity_type,
          original: e,
        }
      }))

    // 应用布局算法（仅对新节点）
    const layoutedNodes = applyIncrementalLayout([...nodes, ...newNodes], edges)

    addNodes(layoutedNodes.slice(nodes.length))
    addEdges(transformRelationsToEdges(result.newRelations))
  }

  return (
    <Sheet>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{selectedNode.data.label}</SheetTitle>
        </SheetHeader>

        <div className="space-y-4">
          <div>
            <Label>Type</Label>
            <Badge>{selectedNode.data.entityType}</Badge>
          </div>

          <Button
            onClick={handleExpandNeighbors}
            disabled={expandNeighbors.isPending}
          >
            {expandNeighbors.isPending ? 'Expanding...' : 'Expand Neighbors'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

### 错误处理和权限

#### RBAC 权限错误处理

```typescript
// 在 API 拦截器中处理 403 错误
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 403) {
      const message = error.response.data?.detail || 'You do not have permission to access this resource'

      toast({
        title: 'Permission Denied',
        description: message,
        variant: 'destructive',
      })

      // 重定向到权限错误页面或主页
      // navigate('/')
    }

    return Promise.reject(error)
  }
)
```

#### 空状态处理

```typescript
// 在 GraphPage.tsx 中
if (!subgraphLoading && (!subgraphData || subgraphData.entities.length === 0)) {
  return (
    <Card className="p-8 text-center">
      <div className="flex flex-col items-center gap-4">
        <Network className="h-12 w-12 text-muted-foreground" />
        <div>
          <h3 className="text-lg font-semibold">No Knowledge Graph Data</h3>
          <p className="text-sm text-muted-foreground">
            Upload documents to extract entities and build the knowledge graph.
          </p>
        </div>
        <Button onClick={() => navigate(`/spaces/${spaceId}/documents`)}>
          Go to Documents
        </Button>
      </div>
    </Card>
  )
}
```

### API 映射对照表

| Yuxi-Know API | Langflow API | 参数映射 | 响应映射 |
|---------------|--------------|---------|---------|
| `GET /api/graph/subgraph?db_id=X&node_label=*&max_depth=2` | `POST /graphs/{space_id}/subgraph` + body | `db_id` → `space_id` (路径参数)<br>`node_label=*` → `entity_ids: [...]` (需先获取)<br>`max_depth` → `max_depth` (body) | `nodes` → `entities`<br>`edges` → `relations` |
| `GET /api/entities?db_id=X&search=Y` | `GET /entities/?space_id=X&search=Y` | `db_id` → `space_id`<br>`search` → `search` | 直接映射 |
| 无对应 API | `GET /graphs/{space_id}/entity/{entity_id}/relations` | 新功能：扩展邻居 | 新响应格式 |
| 无对应 API | `GET /graphs/{space_id}/stats` | 新功能：统计信息 | 新响应格式 |

## 实施阶段（8 周）

### 阶段 1：基础（第 1 周）

**创建文件结构：**
```
src/frontend/src/
├── pages/SpaceDetailPage/GraphPage.tsx
├── components/knowledge-graph/
│   ├── GraphCanvas.tsx
│   ├── GraphControls.tsx
│   ├── GraphDetailPanel.tsx
│   ├── GraphLegend.tsx
│   ├── GraphSearchBar.tsx
│   └── nodes/
│       ├── EntityNode.tsx
│       └── RelationEdge.tsx
├── stores/graphStore.ts
├── controllers/API/queries/graphs/
│   ├── use-get-subgraph.ts
│   ├── use-get-neighbors.ts
│   ├── use-get-shortest-path.ts
│   └── use-get-graph-stats.ts
├── types/api/graphs.ts
└── utils/graphTransform.ts
```

**更新路由和导航：**
- 添加 `/spaces/:spaceId/graph` 路由
- 在 SpaceDetailLayout 添加"Graph"标签

**交付物：**
- [ ] 所有文件和目录创建
- [ ] TypeScript 类型定义完整
- [ ] 路由和导航配置完成

### 阶段 2：核心可视化（第 2-4 周）

**React Query Hooks：**
- `use-get-subgraph.ts` - 获取子图数据
- `use-get-neighbors.ts` - 获取邻居节点
- `use-get-graph-stats.ts` - 获取统计信息

**Zustand Store (`graphStore.ts`)：**
- 状态：nodes, edges, selectedNodeId, filters, layoutType
- 操作：setNodes, addNodes, selectNode, clearSelection

**数据转换 (`graphTransform.ts`)：**
- `transformEntitiesToNodes()` - Entity → GraphNode
- `transformRelationsToEdges()` - Relation → GraphEdge
- `applyDagreLayout()` - Dagre 层次布局
- `getEntityTypeColor()` - 类型颜色映射

**自定义组件：**
- **EntityNode.tsx**：圆形节点，根据 degree 调整大小，颜色编码
- **RelationEdge.tsx**：贝塞尔曲线，显示标签，箭头

**GraphCanvas.tsx**：
- ReactFlow 集成（Background, Controls, MiniMap）
- 自定义 nodeTypes 和 edgeTypes
- 事件处理（onClick, onPaneClick）

**交付物：**
- [ ] 所有 API hooks 实现
- [ ] Zustand store 完整
- [ ] 自定义节点和边组件
- [ ] GraphCanvas 正确渲染

### 阶段 3：UI 组件（第 5-6 周）

**GraphControls.tsx**：
- 缩放按钮（ZoomIn, ZoomOut, Fit View）
- 布局切换（Force/Hierarchical/Dagre）

**GraphLegend.tsx**：
- 实体类型列表（颜色 + 数量）
- 关系类型列表
- 总节点/边数统计

**GraphDetailPanel.tsx**：
- 显示选中实体/关系详情
- "Expand Neighbors"按钮
- 右侧滑入动画（320px 宽）

**GraphSearchBar.tsx**：
- 实时搜索输入
- 实体类型过滤器（Popover + Checkbox）
- 搜索时自动聚焦节点

**交付物：**
- [ ] 所有 UI 组件功能正常
- [ ] Expand Neighbors 工作
- [ ] 搜索和过滤正常

### 阶段 4：集成（第 6-7 周）

**GraphPage.tsx 实现：**
```typescript
export default function GraphPage() {
  const { spaceId } = useParams();
  const { data, isLoading } = useGetSubgraphQuery({
    search_space_id: Number(spaceId),
    max_depth: 2
  });

  // 数据转换 + 布局应用
  // Loading/Empty/Error 状态处理
  // GraphCanvasProvider 包装

  return (
    <div>
      <Header + SearchBar />
      <GraphCanvasProvider>
        <GraphCanvas />
        <GraphDetailPanel />
      </GraphCanvasProvider>
    </div>
  );
}
```

**集成到 Space 布局：**
- Tab 导航：Chats | Notes | Documents | **Graph**
- Detail Panel 打开时调整 Canvas 宽度

**交付物：**
- [ ] GraphPage 完全集成
- [ ] Tab 导航正常
- [ ] Loading/Empty 状态实现
- [ ] 真实数据渲染

### 阶段 5：高级功能（第 7-8 周，可选）

**ShortestPathFinder.tsx**：
- 源/目标实体选择器
- "Find Shortest Path"按钮
- 路径高亮显示

**GraphStatsPanel.tsx**：
- 实体/关系总数（带图标）
- 类型分组统计

**NodeContextMenu.tsx**：
- 右键菜单（View/Expand/Delete）

**交付物：**
- [ ] 最短路径功能
- [ ] 统计面板
- [ ] 右键菜单

### 阶段 6：测试与优化（第 8 周）

**功能测试：**
- [ ] 图谱加载正确
- [ ] 节点/边选择高亮
- [ ] Detail panel 显示准确
- [ ] Expand Neighbors 添加节点
- [ ] 搜索和过滤正常
- [ ] 布局切换正常

**性能测试：**
- [ ] 100 节点：< 500ms
- [ ] 500 节点：< 2s
- [ ] 1000 节点：< 5s
- [ ] 无内存泄漏

**优化：**
- 代码分割（lazy load GraphPage）
- 记忆化（useMemo filteredNodes）
- React Query 缓存配置

**可访问性：**
- [ ] 键盘导航
- [ ] ARIA 标签
- [ ] 颜色对比度 WCAG AA

**交付物：**
- [ ] 所有测试通过
- [ ] 性能达标
- [ ] A11y 合规

## 验证计划

### 端到端测试场景

**场景 1：基础加载**
1. 导航到 Space → Graph 标签
2. 验证 loading 状态
3. 验证节点/边渲染
4. 验证图例显示

**场景 2：节点交互**
1. 点击节点
2. 验证 detail panel 打开
3. 点击"Expand Neighbors"
4. 验证新节点添加

**场景 3：搜索过滤**
1. 输入实体名称
2. 验证匹配节点高亮
3. 选择实体类型过滤
4. 验证图谱更新

**场景 4：布局切换**
1. 选择 Dagre 布局
2. 验证层次排列
3. 选择 Force 布局
4. 验证力导向布局

**场景 5：空状态**
1. 导航到无实体的 Space
2. 验证 empty 状态卡片

### 性能基准

| 节点数 | 渲染时间 | 内存使用 |
|--------|----------|----------|
| 10     | < 100ms  | < 20MB   |
| 100    | < 500ms  | < 50MB   |
| 500    | < 2s     | < 100MB  |
| 1000   | < 5s     | < 200MB  |

## 风险缓解

### 高风险

**1. 大数据集性能**
- 缓解：分页加载、虚拟化、性能基准

**2. ReactFlow vs G6 功能对等**
- 缓解：早期识别关键功能、自定义组件

**3. 布局算法**
- 缓解：从 Dagre 开始、逐步添加 Force

### 中等风险

**1. API 响应时间**
- 缓解：Loading 状态、深度限制、缓存

**2. 状态管理复杂性**
- 缓解：简化 store、分离 UI/数据状态

## 成功标准

**MVP（必须有）：**
- ✅ 图谱渲染实体和关系
- ✅ 节点选择显示详情
- ✅ 搜索功能
- ✅ 基本控制（缩放、平移、适应）
- ✅ 至少一种布局
- ✅ 暗色模式

**应该有：**
- ✅ Expand Neighbors
- ✅ 类型过滤
- ✅ 多种布局
- ✅ 图例
- ✅ 500+ 节点性能

**最好有：**
- ✅ 最短路径
- ✅ 统计面板
- ✅ 右键菜单

## 下一步行动

1. **审查计划** - 确认需求和时间表
2. **开始阶段 1** - 创建文件结构
3. **迭代开发** - 每阶段完成后测试

---

**版本：** 1.0
**更新：** 2026-01-08
**状态：** 准备实施
