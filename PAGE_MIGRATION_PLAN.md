# SurfSense 页面迁移到 Langflow 完整计划

> **生成时间**: 2026-01-04
> **状态**: 规划阶段

## 执行摘要

将 SurfSense 的 47 个 Next.js 页面迁移到 Langflow 的 React Router 系统，保持两个系统的功能完整性，优先使用 SurfSense 页面但保留 Langflow 核心功能。

---

## 📊 路由结构对比分析

### SurfSense 路由结构 (Next.js App Router)

```
app/
├── (home)/              # 营销和公开页面组
│   ├── page.tsx         # 首页 → /
│   ├── login/           # 登录 → /login
│   ├── register/        # 注册 → /register
│   ├── pricing/         # 定价 → /pricing
│   ├── contact/         # 联系 → /contact
│   ├── privacy/         # 隐私政策 → /privacy
│   └── terms/           # 服务条款 → /terms
├── auth/
│   └── callback/        # OAuth 回调 → /auth/callback
├── dashboard/
│   ├── searchspaces/    # 搜索空间列表 → /dashboard/searchspaces
│   ├── api-key/         # API密钥管理 → /dashboard/api-key
│   └── [search_space_id]/  # 动态路由
│       ├── chat/        # 聊天 → /dashboard/:id/chat
│       ├── notes/       # 笔记 → /dashboard/:id/notes
│       ├── connectors/  # 连接器管理
│       │   ├── (manage)/      → /dashboard/:id/connectors
│       │   ├── [connector_id]/→ /dashboard/:id/connectors/:connector_id
│       │   └── add/     # 20+ 连接器添加页面
│       ├── documents/   # 文档管理 → /dashboard/:id/documents
│       ├── logs/        # 日志 → /dashboard/:id/logs
│       ├── model-configs/ # 模型配置 → /dashboard/:id/model-configs
│       ├── roles/       # 角色管理 → /dashboard/:id/roles
│       ├── members/     # 成员管理 → /dashboard/:id/members
│       └── invites/     # 邀请管理 → /dashboard/:id/invites
├── invite/
│   └── [invite_code]/   # 邀请接受 → /invite/:code
├── docs/
│   └── [[...slug]]/     # 文档 → /docs/*
└── api/                 # API 路由（不迁移，后端处理）
```

**总计**: 47 个页面

### Langflow 路由结构 (React Router v6)

```
routes.tsx 定义：
/
├── /login              # 登录页面 ✅ 已有
├── /signup             # 注册页面 ✅ 已有
├── /                   # 主页（重定向到 /flows）
│   ├── /flows          # Flow 列表 ✅ Langflow 核心
│   ├── /components     # 组件列表 ✅ Langflow 核心
│   ├── /all            # 所有项目
│   ├── /mcp            # MCP 服务器
│   ├── /assets
│   │   ├── /files      # 文件管理
│   │   └── /knowledge-bases  # 知识库
│   └── /settings       # 设置 ✅ Langflow 核心
│       ├── /general
│       ├── /global-variables
│       ├── /datasources
│       ├── /mcp-servers
│       ├── /api-keys   # ⚠️ 冲突
│       ├── /shortcuts
│       └── /messages
├── /flow/:id           # Flow 编辑器 ✅ Langflow 核心
├── /flow/:id/view      # Flow 查看
├── /playground/:id     # Playground
├── /admin              # 管理页面
└── /account/delete     # 删除账户
```

---

## 🔄 路由冲突解决策略

### 冲突识别

| 路由 | SurfSense | Langflow | 优先级 | 解决方案 |
|------|-----------|----------|--------|---------|
| `/` | 营销首页 | 重定向到 /flows | SurfSense | 保留 SurfSense，Langflow flows 移至 `/app/flows` |
| `/login` | SurfSense 登录 | Langflow 登录 | SurfSense | 替换 Langflow 登录为 SurfSense 登录 |
| `/signup` (SS: register) | SurfSense 注册 | Langflow 注册 | SurfSense | 替换 Langflow 注册为 SurfSense 注册 |
| `/settings/api-keys` | ❌ 无 | Langflow API密钥 | 合并 | SurfSense `/dashboard/api-key` 集成到 Langflow settings |
| `/dashboard/*` | SurfSense 仪表板 | ❌ 无 | SurfSense | 新增 SurfSense 仪表板路由 |
| `/flows`, `/components` | ❌ 无 | Langflow 核心 | Langflow | 保留 Langflow 核心功能 |

### 路由整合方案

**方案 1: 路径前缀隔离**（推荐）

```typescript
// 新的路由结构
/                          → SurfSense 营销首页
/pricing                   → SurfSense 定价页
/contact                   → SurfSense 联系页
/login                     → SurfSense 登录（替换 Langflow）
/register                  → SurfSense 注册
/auth/callback             → SurfSense OAuth 回调

/app/*                     → Langflow 应用区域（添加 /app 前缀）
/app/flows                 → Langflow Flow 列表
/app/components            → Langflow 组件列表
/app/flow/:id              → Langflow Flow 编辑器
/app/settings/*            → Langflow 设置

/dashboard/*               → SurfSense 仪表板区域
/dashboard/searchspaces    → 搜索空间列表
/dashboard/:id/chat        → AI 聊天
/dashboard/:id/notes       → 笔记管理
/dashboard/:id/connectors  → 连接器管理
/dashboard/:id/documents   → 文档管理
/dashboard/:id/model-configs → 模型配置

/invite/:code              → SurfSense 邀请
/docs/*                    → SurfSense 文档
```

**优势:**
- 清晰分离两个系统
- 无路由冲突
- 易于维护和理解
- 逐步迁移可行

**方案 2: 功能合并**（复杂但用户体验更好）

```typescript
/                          → SurfSense 营销首页
/login                     → SurfSense 登录
/app                       → 统一应用入口（智能重定向）
/flows                     → Langflow Flow 列表
/spaces                    → SurfSense 搜索空间（原 dashboard/searchspaces）
/spaces/:id/chat           → AI 聊天
/spaces/:id/flows          → 该空间的 Langflow flows
/spaces/:id/connectors     → 连接器管理
/spaces/:id/documents      → 文档管理
/settings                  → 合并的设置页面
```

**优势:**
- 统一用户体验
- 自然的功能集成

**劣势:**
- 需要大量重构
- 迁移复杂度高

---

## 📋 迁移策略（采用方案 1 - 路径前缀隔离）

### 阶段 1: 营销和公开页面（优先级: P0）

**目标**: 迁移 SurfSense 首页和营销页面

#### 1.1 首页和营销页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/(home)/page.tsx` | `src/frontend/src/pages/HomePage/` | `/` | 营销首页，保留 Langflow 访问 |
| `app/(home)/pricing/page.tsx` | `src/frontend/src/pages/PricingPage/` | `/pricing` | 定价页 |
| `app/(home)/contact/page.tsx` | `src/frontend/src/pages/ContactPage/` | `/contact` | 联系页 |
| `app/(home)/privacy/page.tsx` | `src/frontend/src/pages/PrivacyPage/` | `/privacy` | 隐私政策 |
| `app/(home)/terms/page.tsx` | `src/frontend/src/pages/TermsPage/` | `/terms` | 服务条款 |

**迁移任务:**
1. 创建 React Router 页面组件
2. 移除 Next.js 特定代码 (`"use client"`, `useRouter()`)
3. 适配为 React Router (`useNavigate()`, `Link from react-router-dom`)
4. 更新路由配置

**保留 Langflow 访问:**
```typescript
// 在首页添加入口按钮
<Link to="/app/flows">
  <Button>进入 Langflow 工作区</Button>
</Link>
```

#### 1.2 首页 Layout 迁移

| 源文件 | 目标位置 | 说明 |
|--------|---------|------|
| `app/(home)/layout.tsx` | `src/frontend/src/pages/HomePage/HomeLayout.tsx` | 营销页面布局 |

**包含组件:**
- Navigation Header
- Footer
- 主题切换

---

### 阶段 2: 认证页面（优先级: P0）

**目标**: 替换 Langflow 登录/注册为 SurfSense 版本

#### 2.1 登录页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/(home)/login/page.tsx` | `src/frontend/src/pages/LoginPage/` | `/login` | 替换 Langflow LoginPage |

**迁移任务:**
1. 保留 Langflow 认证逻辑 (`useAuthStore`)
2. 适配 SurfSense UI 到 Langflow 认证
3. 集成 OAuth 回调
4. 测试登录流程

**关键适配点:**
```typescript
// SurfSense 使用 Supabase Auth
// Langflow 使用自定义认证
// 需要适配认证 API 调用

// 原 SurfSense
const { data, error } = await supabase.auth.signInWithPassword({
  email, password
});

// 适配为 Langflow
const { login } = useAuthStore();
await login({ username: email, password });
```

#### 2.2 注册页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/(home)/register/page.tsx` | `src/frontend/src/pages/SignUpPage/` | `/signup` | 替换 Langflow SignUpPage |

#### 2.3 OAuth 回调

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/auth/callback/page.tsx` | `src/frontend/src/pages/AuthCallbackPage/` | `/auth/callback` | OAuth 回调处理 |

---

### 阶段 3: Dashboard 核心页面（优先级: P1）

**目标**: 迁移 SurfSense 仪表板核心功能

#### 3.1 搜索空间管理

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/searchspaces/page.tsx` | `src/frontend/src/pages/DashboardPage/SearchSpacesPage/` | `/dashboard/searchspaces` | 搜索空间列表 |

**集成点:**
- 与 Langflow spaces API 集成
- 显示现有 spaces
- 支持创建/编辑/删除

#### 3.2 API 密钥管理

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/api-key/page.tsx` | 集成到 Langflow `/app/settings/api-keys` | `/app/settings/api-keys` | 合并到 Langflow 设置 |

**集成策略:**
- 增强 Langflow 现有 API密钥页面
- 添加 SurfSense API密钥功能
- 统一 UI

---

### 阶段 4: Space 详情页面（优先级: P1）

**目标**: 迁移搜索空间内的功能页面

#### 4.1 AI 聊天页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/chat/page.tsx` | `src/frontend/src/pages/DashboardPage/ChatPage/` | `/dashboard/:id/chat` | AI 聊天界面 |

**使用已迁移组件:**
- `Thread` 组件（已迁移）
- `ChatHeader` 组件（已迁移）
- `ModelSelector` 组件（已迁移）

**集成任务:**
1. 连接到 Langflow LLM configs API
2. 集成 Thread 持久化
3. 集成文档提及系统

#### 4.2 笔记管理页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/notes/page.tsx` | `src/frontend/src/pages/DashboardPage/NotesPage/` | `/dashboard/:id/notes` | 笔记列表和编辑 |
| `app/dashboard/[search_space_id]/notes/[note_id]/page.tsx` | `src/frontend/src/pages/DashboardPage/NoteEditorPage/` | `/dashboard/:id/notes/:noteId` | 单个笔记编辑 |

**使用已迁移组件:**
- `BlockNoteEditor` 组件（已迁移）

#### 4.3 文档管理页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/documents/page.tsx` | `src/frontend/src/pages/DashboardPage/DocumentsPage/` | `/dashboard/:id/documents` | 文档列表和管理 |

**使用已迁移组件:**
- `DocumentViewer` 组件（已迁移）
- `DocumentsDataTable` 组件（待迁移）

#### 4.4 连接器管理页面

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/connectors/(manage)/page.tsx` | `src/frontend/src/pages/DashboardPage/ConnectorsPage/` | `/dashboard/:id/connectors` | 连接器列表 |
| `app/dashboard/[search_space_id]/connectors/[connector_id]/page.tsx` | `src/frontend/src/pages/DashboardPage/ConnectorDetailPage/` | `/dashboard/:id/connectors/:connectorId` | 连接器详情 |
| `app/dashboard/[search_space_id]/connectors/[connector_id]/edit/page.tsx` | `src/frontend/src/pages/DashboardPage/ConnectorEditPage/` | `/dashboard/:id/connectors/:connectorId/edit` | 编辑连接器 |

**使用已迁移组件:**
- `ConnectorsTab` 组件（已迁移）
- `EditConnector/*` 组件（已迁移）

---

### 阶段 5: 连接器添加页面（优先级: P2）

**目标**: 迁移 20+ 连接器类型添加页面

#### 5.1 所有连接器添加页面

| 连接器类型 | 源文件路径 | 目标路径 | 路由 |
|-----------|-----------|---------|------|
| GitHub | `app/dashboard/[search_space_id]/connectors/add/github-connector/page.tsx` | `src/frontend/src/pages/DashboardPage/ConnectorAddPages/GitHubConnectorPage.tsx` | `/dashboard/:id/connectors/add/github` |
| Notion | `.../notion-connector/page.tsx` | `.../NotionConnectorPage.tsx` | `/dashboard/:id/connectors/add/notion` |
| Google Gmail | `.../google-gmail-connector/page.tsx` | `.../GoogleGmailConnectorPage.tsx` | `/dashboard/:id/connectors/add/google-gmail` |
| Google Calendar | `.../google-calendar-connector/page.tsx` | `.../GoogleCalendarConnectorPage.tsx` | `/dashboard/:id/connectors/add/google-calendar` |
| Slack | `.../slack-connector/page.tsx` | `.../SlackConnectorPage.tsx` | `/dashboard/:id/connectors/add/slack` |
| Luma | `.../luma-connector/page.tsx` | `.../LumaConnectorPage.tsx` | `/dashboard/:id/connectors/add/luma` |
| Jira | `.../jira-connector/page.tsx` | `.../JiraConnectorPage.tsx` | `/dashboard/:id/connectors/add/jira` |
| Linear | `.../linear-connector/page.tsx` | `.../LinearConnectorPage.tsx` | `/dashboard/:id/connectors/add/linear` |
| Discord | `.../discord-connector/page.tsx` | `.../DiscordConnectorPage.tsx` | `/dashboard/:id/connectors/add/discord` |
| ClickUp | `.../clickup-connector/page.tsx` | `.../ClickUpConnectorPage.tsx` | `/dashboard/:id/connectors/add/clickup` |
| Airtable | `.../airtable-connector/page.tsx` | `.../AirtableConnectorPage.tsx` | `/dashboard/:id/connectors/add/airtable` |
| Elasticsearch | `.../elasticsearch-connector/page.tsx` | `.../ElasticsearchConnectorPage.tsx` | `/dashboard/:id/connectors/add/elasticsearch` |
| Bookstack | `.../bookstack-connector/page.tsx` | `.../BookstackConnectorPage.tsx` | `/dashboard/:id/connectors/add/bookstack` |
| SearXNG | `.../searxng/page.tsx` | `.../SearXNGConnectorPage.tsx` | `/dashboard/:id/connectors/add/searxng` |
| Baidu Search API | `.../baidu-search-api/page.tsx` | `.../BaiduSearchAPIPage.tsx` | `/dashboard/:id/connectors/add/baidu-search` |
| Linkup API | `.../linkup-api/page.tsx` | `.../LinkupAPIPage.tsx` | `/dashboard/:id/connectors/add/linkup` |
| Tavily API | `.../tavily-api/page.tsx` | `.../TavilyAPIPage.tsx` | `/dashboard/:id/connectors/add/tavily` |

**迁移策略:**
- 使用统一的连接器添加模板
- 复用连接器配置组件
- 集成 OAuth 流程

---

### 阶段 6: 高级管理页面（优先级: P2）

**目标**: 迁移团队协作和配置管理页面

#### 6.1 角色和权限管理

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/roles/page.tsx` | `src/frontend/src/pages/DashboardPage/RolesPage/` | `/dashboard/:id/roles` | 角色管理 |
| `app/dashboard/[search_space_id]/members/page.tsx` | `src/frontend/src/pages/DashboardPage/MembersPage/` | `/dashboard/:id/members` | 成员管理 |
| `app/dashboard/[search_space_id]/invites/page.tsx` | `src/frontend/src/pages/DashboardPage/InvitesPage/` | `/dashboard/:id/invites` | 邀请管理 |

#### 6.2 模型和日志管理

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/dashboard/[search_space_id]/model-configs/page.tsx` | `src/frontend/src/pages/DashboardPage/ModelConfigsPage/` | `/dashboard/:id/model-configs` | 模型配置 |
| `app/dashboard/[search_space_id]/logs/page.tsx` | `src/frontend/src/pages/DashboardPage/LogsPage/` | `/dashboard/:id/logs` | 系统日志 |

---

### 阶段 7: 其他功能页面（优先级: P3）

#### 7.1 邀请和文档

| 源文件 | 目标位置 | 路由 | 说明 |
|--------|---------|------|------|
| `app/invite/[invite_code]/page.tsx` | `src/frontend/src/pages/InvitePage/` | `/invite/:code` | 接受邀请 |
| `app/docs/[[...slug]]/page.tsx` | `src/frontend/src/pages/DocsPage/` | `/docs/*` | 文档浏览 |

---

## 🔧 技术迁移模式

### Next.js → React Router 转换规则

#### 1. 页面组件转换

**Next.js App Router:**
```typescript
// app/dashboard/chat/page.tsx
"use client";

export default function ChatPage() {
  return <div>Chat</div>;
}
```

**React Router:**
```typescript
// src/frontend/src/pages/DashboardPage/ChatPage/index.tsx
export default function ChatPage() {
  return <div>Chat</div>;
}
```

#### 2. 动态路由参数

**Next.js:**
```typescript
// app/dashboard/[search_space_id]/page.tsx
export default function SpacePage({ params }: { params: { search_space_id: string } }) {
  const { search_space_id } = params;
}
```

**React Router:**
```typescript
// src/frontend/src/pages/DashboardPage/SpacePage/index.tsx
import { useParams } from "react-router-dom";

export default function SpacePage() {
  const { spaceId } = useParams<{ spaceId: string }>();
}
```

#### 3. 导航和链接

**Next.js:**
```typescript
import { useRouter } from "next/navigation";
import Link from "next/link";

const router = useRouter();
router.push("/dashboard");

<Link href="/dashboard">Dashboard</Link>
```

**React Router:**
```typescript
import { useNavigate, Link } from "react-router-dom";

const navigate = useNavigate();
navigate("/dashboard");

<Link to="/dashboard">Dashboard</Link>
```

#### 4. Metadata 处理

**Next.js:**
```typescript
export const metadata = {
  title: "Chat",
  description: "AI Chat Interface"
};
```

**React Router (使用 React Helmet):**
```typescript
import { Helmet } from "react-helmet-async";

function ChatPage() {
  return (
    <>
      <Helmet>
        <title>Chat</title>
        <meta name="description" content="AI Chat Interface" />
      </Helmet>
      {/* Page content */}
    </>
  );
}
```

---

## 📁 目标目录结构

```
src/frontend/src/pages/
├── HomePage/                    # 营销首页（SurfSense）
│   ├── index.tsx
│   └── HomeLayout.tsx
├── PricingPage/                 # 定价页（SurfSense）
├── ContactPage/                 # 联系页（SurfSense）
├── PrivacyPage/                 # 隐私政策（SurfSense）
├── TermsPage/                   # 服务条款（SurfSense）
├── LoginPage/                   # 登录（SurfSense 替换 Langflow）
├── SignUpPage/                  # 注册（SurfSense 替换 Langflow）
├── AuthCallbackPage/            # OAuth 回调（SurfSense）
├── DashboardPage/               # Dashboard 页面组
│   ├── SearchSpacesPage/        # 搜索空间列表
│   ├── ChatPage/                # AI 聊天
│   ├── NotesPage/               # 笔记列表
│   ├── NoteEditorPage/          # 笔记编辑器
│   ├── DocumentsPage/           # 文档管理
│   ├── ConnectorsPage/          # 连接器列表
│   ├── ConnectorDetailPage/     # 连接器详情
│   ├── ConnectorEditPage/       # 编辑连接器
│   ├── ConnectorAddPages/       # 连接器添加页面
│   │   ├── GitHubConnectorPage.tsx
│   │   ├── NotionConnectorPage.tsx
│   │   ├── GoogleGmailConnectorPage.tsx
│   │   ├── GoogleCalendarConnectorPage.tsx
│   │   └── ...（20+ 连接器）
│   ├── RolesPage/               # 角色管理
│   ├── MembersPage/             # 成员管理
│   ├── InvitesPage/             # 邀请管理
│   ├── ModelConfigsPage/        # 模型配置
│   └── LogsPage/                # 系统日志
├── InvitePage/                  # 接受邀请（SurfSense）
├── DocsPage/                    # 文档浏览（SurfSense）
│
# Langflow 原有页面（保留，添加 /app 前缀）
├── MainPage/                    # Langflow 主页（/app/flows, /app/components）
├── FlowPage/                    # Langflow Flow 编辑器（/app/flow/:id）
├── SettingsPage/                # Langflow 设置（/app/settings）
├── AdminPage/                   # Langflow 管理（/app/admin）
└── ViewPage/                    # Langflow Flow 查看（/app/flow/:id/view）
```

---

## 🔀 路由配置更新

### 新的 routes.tsx 结构

```typescript
// src/frontend/src/routes.tsx
import { createBrowserRouter, createRoutesFromElements, Route } from "react-router-dom";

// SurfSense 页面导入
import HomePage from "./pages/HomePage";
import PricingPage from "./pages/PricingPage";
import ContactPage from "./pages/ContactPage";
import LoginPage from "./pages/LoginPage";  // 替换 Langflow LoginPage
import SignUpPage from "./pages/SignUpPage";  // 替换 Langflow SignUpPage
import AuthCallbackPage from "./pages/AuthCallbackPage";

// Dashboard 页面导入
import SearchSpacesPage from "./pages/DashboardPage/SearchSpacesPage";
import ChatPage from "./pages/DashboardPage/ChatPage";
import NotesPage from "./pages/DashboardPage/NotesPage";
// ... 其他 dashboard 页面

// Langflow 原有页面（保留）
import LangflowHomePage from "./pages/MainPage/pages/homePage";
import FlowPage from "./pages/FlowPage";
import LangflowSettingsPage from "./pages/SettingsPage";

const router = createBrowserRouter(
  createRoutesFromElements([
    // === SurfSense 公开页面 ===
    <Route path="/" element={<HomeLayout />}>
      <Route index element={<HomePage />} />
      <Route path="pricing" element={<PricingPage />} />
      <Route path="contact" element={<ContactPage />} />
      <Route path="privacy" element={<PrivacyPage />} />
      <Route path="terms" element={<TermsPage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<SignUpPage />} />
    </Route>,

    // === SurfSense Auth ===
    <Route path="/auth/callback" element={<AuthCallbackPage />} />,

    // === SurfSense Dashboard（需要认证）===
    <Route
      path="/dashboard"
      element={
        <ProtectedRoute>
          <DashboardLayout />
        </ProtectedRoute>
      }
    >
      <Route path="searchspaces" element={<SearchSpacesPage />} />

      {/* Space 详情页面 */}
      <Route path=":spaceId">
        <Route path="chat" element={<ChatPage />} />
        <Route path="notes" element={<NotesPage />} />
        <Route path="notes/:noteId" element={<NoteEditorPage />} />
        <Route path="documents" element={<DocumentsPage />} />

        {/* 连接器 */}
        <Route path="connectors">
          <Route index element={<ConnectorsPage />} />
          <Route path=":connectorId" element={<ConnectorDetailPage />} />
          <Route path=":connectorId/edit" element={<ConnectorEditPage />} />

          {/* 连接器添加路由 */}
          <Route path="add">
            <Route path="github" element={<GitHubConnectorPage />} />
            <Route path="notion" element={<NotionConnectorPage />} />
            <Route path="google-gmail" element={<GoogleGmailConnectorPage />} />
            <Route path="google-calendar" element={<GoogleCalendarConnectorPage />} />
            <Route path="slack" element={<SlackConnectorPage />} />
            <Route path="luma" element={<LumaConnectorPage />} />
            {/* ... 其他 20+ 连接器 */}
          </Route>
        </Route>

        {/* 团队管理 */}
        <Route path="roles" element={<RolesPage />} />
        <Route path="members" element={<MembersPage />} />
        <Route path="invites" element={<InvitesPage />} />

        {/* 配置和日志 */}
        <Route path="model-configs" element={<ModelConfigsPage />} />
        <Route path="logs" element={<LogsPage />} />
      </Route>
    </Route>,

    // === Langflow 应用区域（添加 /app 前缀）===
    <Route
      path="/app"
      element={
        <ProtectedRoute>
          <ContextWrapper>
            <AppWrapperPage />
          </ContextWrapper>
        </ProtectedRoute>
      }
    >
      <Route path="flows" element={<LangflowHomePage type="flows" />} />
      <Route path="components" element={<LangflowHomePage type="components" />} />
      <Route path="mcp" element={<LangflowHomePage type="mcp" />} />

      <Route path="flow/:id" element={<FlowPage />} />
      <Route path="flow/:id/view" element={<ViewPage />} />

      <Route path="settings" element={<LangflowSettingsPage />}>
        <Route index element={<Navigate replace to="general" />} />
        <Route path="general" element={<GeneralPage />} />
        <Route path="api-keys" element={<ApiKeysPage />} />
        <Route path="global-variables" element={<GlobalVariablesPage />} />
        <Route path="datasources" element={<DataSourcesPage />} />
        <Route path="mcp-servers" element={<MCPServersPage />} />
        <Route path="shortcuts" element={<ShortcutsPage />} />
        <Route path="messages" element={<MessagesPage />} />
      </Route>

      <Route path="admin" element={<ProtectedAdminRoute><AdminPage /></ProtectedAdminRoute>} />
    </Route>,

    // === 其他路由 ===
    <Route path="/invite/:code" element={<InvitePage />} />,
    <Route path="/docs/*" element={<DocsPage />} />,

    // 404 处理
    <Route path="*" element={<Navigate replace to="/" />} />
  ])
);

export default router;
```

---

## 🎯 迁移优先级总结

### P0 - 立即执行（Week 1-2）

**必须优先迁移的核心页面:**

1. **首页系统** (3 个页面)
   - 首页 `/`
   - 登录 `/login`
   - 注册 `/register`

2. **Dashboard 核心** (2 个页面)
   - 搜索空间列表 `/dashboard/searchspaces`
   - AI 聊天页面 `/dashboard/:id/chat`

**预期成果:**
- 用户可以访问营销首页
- 用户可以登录和注册
- 用户可以进入 Dashboard 并使用 AI 聊天

### P1 - 高优先级（Week 3-4）

**重要功能页面:**

1. **内容管理** (3 个页面)
   - 笔记管理 `/dashboard/:id/notes`
   - 文档管理 `/dashboard/:id/documents`
   - 连接器管理 `/dashboard/:id/connectors`

2. **团队协作** (3 个页面)
   - 角色管理 `/dashboard/:id/roles`
   - 成员管理 `/dashboard/:id/members`
   - 邀请管理 `/dashboard/:id/invites`

**预期成果:**
- 完整的内容创建和管理功能
- 团队协作功能可用

### P2 - 中优先级（Week 5-6）

**扩展功能页面:**

1. **连接器添加页面** (20+ 个页面)
   - 所有第三方服务连接器添加页面

2. **高级功能** (2 个页面)
   - 模型配置 `/dashboard/:id/model-configs`
   - 系统日志 `/dashboard/:id/logs`

**预期成果:**
- 所有连接器类型可添加
- 完整的系统配置和监控

### P3 - 低优先级（Week 7+）

**辅助功能页面:**

1. **营销页面** (3 个页面)
   - 定价 `/pricing`
   - 联系 `/contact`
   - 隐私/条款 `/privacy`, `/terms`

2. **其他功能** (2 个页面)
   - 邀请接受 `/invite/:code`
   - 文档浏览 `/docs/*`

---

## ✅ 验收标准

### 功能完整性

**SurfSense 功能:**
- [ ] 所有 47 个页面成功迁移
- [ ] 所有动态路由正常工作
- [ ] OAuth 认证流程正常
- [ ] 所有连接器添加功能正常
- [ ] 团队协作功能完整

**Langflow 功能:**
- [ ] Langflow Flow 列表可访问（`/app/flows`）
- [ ] Flow 编辑器正常工作（`/app/flow/:id`）
- [ ] Langflow 设置页面保留（`/app/settings`）
- [ ] API 密钥管理正常
- [ ] 全局变量管理正常

### 路由测试

- [ ] 所有路由可以正确导航
- [ ] 动态参数正确解析
- [ ] 嵌套路由正常工作
- [ ] 404 页面正确显示
- [ ] 路由保护正常（认证检查）

### 用户体验

- [ ] 页面加载速度正常
- [ ] 页面切换动画流畅
- [ ] 面包屑导航正确
- [ ] 浏览器后退/前进正常
- [ ] 深度链接可分享

### 集成测试

- [ ] 认证状态在路由间保持
- [ ] 全局状态正确更新
- [ ] API 调用正常
- [ ] 国际化正常工作
- [ ] 主题切换保持

---

## 📝 迁移检查清单

### 每个页面迁移清单

**代码转换:**
- [ ] 移除 `"use client"` 指令
- [ ] 替换 `useRouter()` 为 `useNavigate()`
- [ ] 替换 `usePathname()` 为 `useLocation()`
- [ ] 替换 `useSearchParams()` 为 `useSearchParams()`
- [ ] 替换 `Link from "next/link"` 为 `Link from "react-router-dom"`
- [ ] 替换 `params` prop 为 `useParams()` hook
- [ ] 移除 Next.js metadata，使用 React Helmet
- [ ] 移除 Next.js Image，使用标准 `<img>`

**状态管理:**
- [ ] 替换 Jotai atoms 为 Zustand stores
- [ ] 适配 Supabase API 为 Langflow API
- [ ] 更新 API 调用使用 React Query hooks

**样式:**
- [ ] 验证 Tailwind 类名兼容 v3
- [ ] 测试明暗主题切换
- [ ] 检查响应式布局

**国际化:**
- [ ] 替换 `useTranslations()` 为 `useTranslation()`
- [ ] 验证翻译键存在

**测试:**
- [ ] 页面正常渲染
- [ ] 路由导航正常
- [ ] 所有交互功能正常
- [ ] API 调用正常
- [ ] 错误处理正常

---

## 🚀 实施路线图

### Week 1: 首页和认证（P0）

**Day 1-2:**
- 迁移首页 `/`
- 创建 HomeLayout
- 测试首页组件集成

**Day 3-4:**
- 迁移登录页面 `/login`
- 迁移注册页面 `/register`
- 适配认证 API

**Day 5:**
- 迁移 OAuth 回调 `/auth/callback`
- 测试完整认证流程

### Week 2: Dashboard 核心（P0）

**Day 1-2:**
- 迁移搜索空间列表 `/dashboard/searchspaces`
- 创建 DashboardLayout

**Day 3-5:**
- 迁移 AI 聊天页面 `/dashboard/:id/chat`
- 集成 Thread 组件
- 集成 LLM configs API
- 测试聊天功能

### Week 3: 内容管理（P1）

**Day 1-2:**
- 迁移笔记管理 `/dashboard/:id/notes`
- 集成 BlockNote 编辑器

**Day 3-4:**
- 迁移文档管理 `/dashboard/:id/documents`
- 集成文档 API

**Day 5:**
- 迁移连接器管理 `/dashboard/:id/connectors`
- 测试连接器列表

### Week 4: 团队协作（P1）

**Day 1-2:**
- 迁移角色管理 `/dashboard/:id/roles`
- 迁移成员管理 `/dashboard/:id/members`

**Day 3-4:**
- 迁移邀请管理 `/dashboard/:id/invites`
- 测试团队功能

**Day 5:**
- 集成测试和 bug 修复

### Week 5-6: 连接器添加页面（P2）

**Day 1-10:**
- 批量迁移 20+ 连接器添加页面
- 每天迁移 2-3 个连接器页面
- 测试连接器添加流程

### Week 7+: 其他功能（P3）

**按需迁移:**
- 营销页面（定价、联系等）
- 邀请和文档页面
- 最终集成测试

---

## 📚 相关文档

- [组件迁移报告](./SURFSENSE_MIGRATION_REPORT.md) - 已完成的 31 个组件迁移
- [集成测试计划](./INTEGRATION_TEST_PLAN.md) - 组件测试和功能集成计划
- [依赖状态报告](./DEPENDENCY_STATUS_REPORT.md) - 依赖安装和问题修复

---

**总结**: 47 个页面迁移分 7 周完成，采用路径前缀隔离策略（`/app` 为 Langflow，`/dashboard` 为 SurfSense），保证两个系统功能完整性。优先迁移核心功能（首页、认证、AI 聊天），逐步扩展到完整功能。
