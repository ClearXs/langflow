# Langflow SurfSense 组件集成与测试计划

## 执行摘要

本文档为 SurfSense 组件迁移到 Langflow 后的**测试计划**和**功能集成增强路线图**。当前已完成 **31 个组件** 的迁移（包括 UI、AI 聊天、编辑器、工具和业务组件），下一步需要进行全面测试和功能集成。

---

## 📊 当前迁移状态

### ✅ 已完成迁移组件（31个）

**基础 UI 组件（6个）:**
- avatar.tsx, calendar.tsx, sonner.tsx
- bento-grid.tsx, spotlight.tsx, tilt.tsx

**AI 聊天组件（8个）:**
- thread.tsx (647行 - 简化版)
- thread-list.tsx, attachment.tsx
- inline-citation.tsx, markdown-text.tsx
- tool-fallback.tsx, tooltip-icon-button.tsx
- chain-of-thought.tsx (prompt-kit/)

**编辑器组件（2个）:**
- BlockNoteEditor.tsx (167行)
- DynamicBlockNoteEditor.tsx

**状态管理（2个）:**
- announcementStore.ts
- editorStore.ts (增强版)

**工具组件（11个）:**
- copy-button.tsx
- announcement-banner.tsx
- UserDropdown.tsx
- inference-params-editor.tsx
- LanguageSwitcher.tsx
- json-metadata-viewer.tsx
- markdown-viewer.tsx
- Logo.tsx
- document-viewer.tsx
- dashboard-breadcrumb.tsx

**业务组件（2个）:**
- model-selector.tsx (新 - 简化版)
- chat-header.tsx (新 - 简化版)

### ⏳ 待完成组件（可选）

**复杂业务组件:**
- model-config-sidebar.tsx - LLM 配置侧边栏
- DocumentsDataTable.tsx - 文档数据表格
- source-detail-panel.tsx - 数据源详情面板
- sidebar/* - 侧边栏组件（9个）
- sources/* - 数据源组件（6个）
- settings/* - 设置组件（3个）

**说明:** 这些组件依赖较重的 SurfSense 特定功能，可在 Langflow 相应功能完善后再迁移。

---

## 🧪 阶段 1：基础功能测试（Week 1）

### 目标
验证所有已迁移组件在 Langflow 环境中正常工作。

### 1.1 环境准备

**前置条件：**
```bash
# 1. 确保依赖已安装
cd /Users/jiangwei/Python/langflow
npm install  # 或 yarn install

# 2. 启动后端服务
make backend

# 3. 启动前端服务（新终端）
make frontend

# 4. 访问应用
# Frontend: http://localhost:3000
# Backend: http://localhost:7860
```

**依赖验证：**
检查以下新增依赖是否正确安装：
- @assistant-ui/react@^0.11.53
- @blocknote/react@^0.45.0
- sonner@^2.0.6
- react-day-picker@^9.8.1
- react-dropzone@^14.3.8
- 其他 18+ 个依赖

### 1.2 UI 组件测试

#### 测试 1.2.1: 基础 UI 组件渲染

**组件列表：**
- Avatar, Calendar, Sonner (Toast)
- Bento Grid, Spotlight, Tilt

**测试步骤：**
1. 创建测试页面导入所有 UI 组件
2. 验证组件在明暗主题下正常显示
3. 检查响应式布局
4. 验证交互功能（点击、hover 等）

**验收标准：**
- [ ] 所有组件无 TypeScript 错误
- [ ] 明暗主题切换正常
- [ ] 移动端/桌面端布局正确
- [ ] 无样式冲突或覆盖问题

**测试代码示例：**
```typescript
// src/pages/test/ui-components.tsx
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Calendar } from "@/components/ui/calendar";
import { toast } from "sonner";
import { BentoGrid } from "@/components/ui/bento-grid";

export function UIComponentsTest() {
  const [date, setDate] = useState<Date | undefined>(new Date());

  return (
    <div className="p-8 space-y-8">
      <section>
        <h2>Avatar</h2>
        <Avatar>
          <AvatarImage src="/avatar.jpg" />
          <AvatarFallback>CN</AvatarFallback>
        </Avatar>
      </section>

      <section>
        <h2>Calendar</h2>
        <Calendar mode="single" selected={date} onSelect={setDate} />
      </section>

      <section>
        <h2>Toast</h2>
        <button onClick={() => toast.success("Test toast!")}>
          Show Toast
        </button>
      </section>

      {/* ... other components */}
    </div>
  );
}
```

#### 测试 1.2.2: Toast 通知系统

**测试场景：**
1. 成功/错误/警告/信息 toast
2. Toast 在明暗主题下的显示
3. 多个 toast 同时显示
4. Toast 自动消失

**测试代码：**
```typescript
import { toast } from "sonner";

// Test all toast types
toast.success("Operation successful!");
toast.error("Something went wrong!");
toast.warning("Warning message");
toast.info("Information message");

// Test with custom duration
toast.success("This will stay for 5 seconds", { duration: 5000 });
```

**验收标准：**
- [ ] 所有 toast 类型正常显示
- [ ] 主题适配正确（使用 useDarkStore）
- [ ] 自动消失功能正常
- [ ] 无视觉闪烁或样式问题

### 1.3 AI 聊天组件测试

#### 测试 1.3.1: Thread 组件基础功能

**测试场景：**
1. 组件正常渲染
2. 消息输入框功能
3. 附件上传
4. Markdown 渲染
5. 思考链展示

**测试步骤：**
```typescript
import { Thread } from "@/components/assistant-ui";
import { AssistantRuntimeProvider } from "@assistant-ui/react";

function TestChatPage() {
  return (
    <AssistantRuntimeProvider runtime={mockRuntime}>
      <Thread
        header={<div>Chat Header</div>}
      />
    </AssistantRuntimeProvider>
  );
}
```

**验收标准：**
- [ ] Thread 组件无错误渲染
- [ ] 消息输入框可用
- [ ] 附件上传 UI 显示正确
- [ ] Markdown 正常渲染（代码块、列表、链接等）
- [ ] 思考链组件正常展开/收起

#### 测试 1.3.2: Markdown 渲染功能

**测试用例：**
```typescript
const testMarkdown = `
# Heading 1
## Heading 2

**Bold text** and *italic text*

- List item 1
- List item 2

\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

[Link](https://example.com)

\`inline code\`

> Blockquote

| Table | Header |
|-------|--------|
| Cell  | Cell   |
`;

<MarkdownText content={testMarkdown} />
```

**验收标准：**
- [ ] 所有 Markdown 语法正确渲染
- [ ] 代码块语法高亮正常
- [ ] 链接可点击
- [ ] 表格格式正确
- [ ] 引用块样式正确

#### 测试 1.3.3: 附件功能

**测试场景：**
1. 图片附件上传
2. 图片预览
3. 文件附件上传
4. 附件删除

**测试代码：**
```typescript
import { Attachment } from "@/components/assistant-ui";

function TestAttachment() {
  const [files, setFiles] = useState<File[]>([]);

  return (
    <Attachment
      attachment={{
        type: "image",
        name: "test.jpg",
        contentType: "image/jpeg",
        file: files[0],
      }}
    />
  );
}
```

**验收标准：**
- [ ] 图片正确预览（使用标准 img 标签）
- [ ] 上传状态显示正常
- [ ] 文件类型图标显示
- [ ] 删除功能正常

### 1.4 编辑器组件测试

#### 测试 1.4.1: BlockNote 编辑器

**测试场景：**
1. 编辑器加载和初始化
2. 文本输入和格式化
3. 标题块功能
4. 代码块功能
5. 图片插入
6. 主题切换

**测试代码：**
```typescript
import { Suspense, useState } from "react";
import { BlockNoteEditor } from "@/components/DynamicBlockNoteEditor";

function TestEditor() {
  const [content, setContent] = useState("");

  return (
    <Suspense fallback={<div>Loading editor...</div>}>
      <BlockNoteEditor
        initialContent={content}
        onChange={(newContent) => setContent(newContent)}
        useTitleBlock={true}
      />
    </Suspense>
  );
}
```

**验收标准：**
- [ ] 编辑器正常加载（使用 React.lazy）
- [ ] 明暗主题适配（使用 useDarkStore）
- [ ] 所有格式化功能正常
- [ ] 标题块功能正常
- [ ] 内容保存和加载正常
- [ ] 无性能问题

### 1.5 工具组件测试

#### 测试 1.5.1: 语言切换器

**测试场景：**
1. 语言切换功能
2. localStorage 持久化
3. i18n 集成

**测试代码：**
```typescript
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useTranslation } from "react-i18next";

function TestLanguage() {
  const { t } = useTranslation();

  return (
    <div>
      <LanguageSwitcher />
      <p>{t('common.settings')}</p>
      <p>{t('flows.createNew')}</p>
    </div>
  );
}
```

**验收标准：**
- [ ] 语言切换立即生效
- [ ] 刷新页面后语言保持
- [ ] i18nStore 状态正确更新
- [ ] react-i18next 集成正常

#### 测试 1.5.2: 公告横幅

**测试场景：**
1. 横幅显示
2. 关闭功能
3. localStorage 持久化

**验收标准：**
- [ ] 横幅正确显示
- [ ] 关闭后不再显示
- [ ] 刷新后保持关闭状态
- [ ] announcementStore 正常工作

#### 测试 1.5.3: UserDropdown

**测试场景：**
1. 用户信息显示
2. 菜单项显示
3. 路由导航
4. 登出功能

**验收标准：**
- [ ] 用户头像/名称显示
- [ ] 下拉菜单正常打开
- [ ] 路由导航正确（React Router）
- [ ] 登出清除 token

#### 测试 1.5.4: 其他工具组件

**测试组件：**
- copy-button.tsx
- inference-params-editor.tsx
- json-metadata-viewer.tsx
- markdown-viewer.tsx
- document-viewer.tsx

**验收标准：**
- [ ] 复制按钮功能正常
- [ ] 参数编辑器验证逻辑正确
- [ ] JSON 查看器正确解析和显示
- [ ] Markdown 查看器正常渲染
- [ ] 文档查看器对话框正常

### 1.6 业务组件测试

#### 测试 1.6.1: ModelSelector 组件

**测试场景：**
1. 模型列表显示
2. 搜索功能
3. 模型切换
4. 编辑/新建按钮

**测试代码：**
```typescript
import { ModelSelector } from "@/components/new-chat";
import type { LLMConfigRead } from "@/types/api/llm-configs";

function TestModelSelector() {
  const userConfigs: LLMConfigRead[] = [
    {
      id: 1,
      name: "GPT-4",
      provider: "OPENAI",
      model: "gpt-4",
      temperature: 0.7,
      // ... other fields
    },
  ];

  return (
    <ModelSelector
      userConfigs={userConfigs}
      globalConfigs={[]}
      currentConfig={userConfigs[0]}
      isLoading={false}
      onSelectConfig={async (config) => {
        console.log("Selected:", config);
      }}
      onEdit={(config, isGlobal) => {
        console.log("Edit:", config, isGlobal);
      }}
      onAddNew={() => {
        console.log("Add new");
      }}
    />
  );
}
```

**验收标准：**
- [ ] 模型列表正确显示
- [ ] 搜索过滤功能正常
- [ ] 当前模型高亮显示
- [ ] 切换模型调用 onSelectConfig
- [ ] 编辑按钮调用 onEdit
- [ ] 新建按钮调用 onAddNew
- [ ] 加载状态正确显示
- [ ] Provider 图标正确显示

#### 测试 1.6.2: ChatHeader 组件

**测试场景：**
1. 组件渲染
2. ModelSelector 集成
3. 回调函数传递

**验收标准：**
- [ ] ChatHeader 正常渲染
- [ ] 所有 props 正确传递给 ModelSelector
- [ ] 回调函数正常触发

#### 测试 1.6.3: DashboardBreadcrumb 组件

**测试场景：**
1. 不同路由下的面包屑
2. 路由导航
3. react-i18next 集成

**测试路由：**
- /flows
- /flows/123
- /spaces/456
- /spaces/456/chats
- /settings/api-keys

**验收标准：**
- [ ] 面包屑正确生成
- [ ] 点击导航正常
- [ ] i18n 翻译正常
- [ ] React Router 集成正常

---

## 🔗 阶段 2：功能集成增强（Week 2-3）

### 目标
将简化的组件功能完善，集成到 Langflow 的实际功能中。

### 2.1 Thread 组件功能集成

#### 当前状态
Thread 组件已迁移，但以下功能被简化为占位符：
- 文档提及系统（Document Mentions）
- 连接器指示器（Connector Indicators）
- 线程持久化（Thread Persistence）

#### 集成任务 2.1.1: 文档提及系统

**目标：** 在聊天中支持 `@document` 提及功能

**实现步骤：**

1. **创建文档搜索 API Hook**
```typescript
// src/controllers/API/queries/documents/use-search-documents.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";

export function useSearchDocuments(spaceId: number, query: string) {
  return useQuery({
    queryKey: ["documents", "search", spaceId, query],
    queryFn: async () => {
      const response = await api.get(`/spaces/${spaceId}/documents/search`, {
        params: { q: query },
      });
      return response.data;
    },
    enabled: query.length > 0,
  });
}
```

2. **更新 Thread 组件**
```typescript
// In thread.tsx - Replace placeholder
import { useSearchDocuments } from "@/controllers/API/queries/documents";

// Inside Thread component
const { data: documents } = useSearchDocuments(spaceId, mentionQuery);

// Enable document mention suggestions
const documentSuggestions = documents?.map(doc => ({
  id: doc.id,
  name: doc.title,
  type: "document",
}));
```

3. **创建 DocumentMention 组件**
```typescript
// src/components/assistant-ui/document-mention.tsx
export function DocumentMention({ documentId, documentName }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary/10 text-primary">
      <FileText className="size-3" />
      {documentName}
    </span>
  );
}
```

**验收标准：**
- [ ] @ 符号触发文档搜索
- [ ] 搜索结果实时显示
- [ ] 选择文档插入提及标记
- [ ] 消息中正确渲染文档提及
- [ ] 提及的文档可点击查看

#### 集成任务 2.1.2: 线程持久化

**目标：** 保存和加载聊天线程

**实现步骤：**

1. **创建线程 API**
```typescript
// src/controllers/API/queries/threads/use-create-thread.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";

export function useCreateThread(spaceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { title?: string; messages: any[] }) => {
      const response = await api.post(`/spaces/${spaceId}/threads`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["threads", spaceId] });
    },
  });
}

export function useGetThreads(spaceId: number) {
  return useQuery({
    queryKey: ["threads", spaceId],
    queryFn: async () => {
      const response = await api.get(`/spaces/${spaceId}/threads`);
      return response.data;
    },
  });
}

export function useGetThread(threadId: string) {
  return useQuery({
    queryKey: ["threads", threadId],
    queryFn: async () => {
      const response = await api.get(`/threads/${threadId}`);
      return response.data;
    },
    enabled: !!threadId,
  });
}
```

2. **更新 ThreadList 组件**
```typescript
// In thread-list.tsx - Replace placeholder storage
import { useGetThreads } from "@/controllers/API/queries/threads";

export function ThreadList({ spaceId }: ThreadListProps) {
  const { data: threads, isLoading } = useGetThreads(spaceId);

  // ... rest of implementation
}
```

3. **集成到 Thread 组件**
```typescript
// In thread.tsx
import { useCreateThread, useGetThread } from "@/controllers/API/queries/threads";

export function Thread({ threadId, spaceId }) {
  const { data: thread } = useGetThread(threadId);
  const { mutate: createThread } = useCreateThread(spaceId);

  // Auto-save on new messages
  useEffect(() => {
    if (newMessages.length > 0) {
      createThread({ messages: newMessages });
    }
  }, [newMessages]);
}
```

**验收标准：**
- [ ] 新线程自动创建
- [ ] 线程列表正确显示
- [ ] 点击线程加载历史消息
- [ ] 消息实时保存
- [ ] 线程标题自动生成或手动设置

### 2.2 LLM 配置集成

#### 当前状态
ModelSelector 和 ChatHeader 已迁移，但需要集成到 Langflow 的 LLM 配置系统。

#### 集成任务 2.2.1: 连接 LLM Configs API

**前置条件：**
检查 Langflow 是否已有 LLM configs API：
```bash
# 查找现有 API
grep -r "llm.*config" src/backend/base/langflow/api/v1/
```

**实现步骤：**

1. **创建 LLM Configs Query Hooks**
```typescript
// src/controllers/API/queries/llm-configs/use-get-llm-configs.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type { LLMConfigRead, GlobalLLMConfigRead } from "@/types/api/llm-configs";

export function useGetUserLLMConfigs(spaceId: number) {
  return useQuery<LLMConfigRead[]>({
    queryKey: ["llm-configs", "user", spaceId],
    queryFn: async () => {
      const response = await api.get(`/spaces/${spaceId}/llm-configs`);
      return response.data;
    },
    enabled: !!spaceId,
  });
}

export function useGetGlobalLLMConfigs() {
  return useQuery<GlobalLLMConfigRead[]>({
    queryKey: ["llm-configs", "global"],
    queryFn: async () => {
      const response = await api.get("/llm-configs/global");
      return response.data;
    },
  });
}

export function useGetCurrentLLMConfig(spaceId: number) {
  return useQuery({
    queryKey: ["llm-configs", "current", spaceId],
    queryFn: async () => {
      const response = await api.get(`/spaces/${spaceId}/llm-configs/current`);
      return response.data;
    },
    enabled: !!spaceId,
  });
}
```

2. **创建 Mutation Hooks**
```typescript
// src/controllers/API/queries/llm-configs/use-update-llm-config.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type { LLMConfigUpdate } from "@/types/api/llm-configs";

export function useUpdateCurrentLLMConfig(spaceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (configId: number) => {
      const response = await api.put(
        `/spaces/${spaceId}/llm-configs/current`,
        { llm_config_id: configId }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-configs", "current", spaceId] });
    },
  });
}

export function useCreateLLMConfig(spaceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LLMConfigCreate) => {
      const response = await api.post(`/spaces/${spaceId}/llm-configs`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-configs", "user", spaceId] });
    },
  });
}
```

3. **集成到 ChatHeader**
```typescript
// Example usage in a page component
import { ChatHeader } from "@/components/new-chat";
import {
  useGetUserLLMConfigs,
  useGetGlobalLLMConfigs,
  useGetCurrentLLMConfig,
  useUpdateCurrentLLMConfig,
} from "@/controllers/API/queries/llm-configs";

function ChatPage({ spaceId }: { spaceId: number }) {
  const { data: userConfigs, isLoading: userLoading } = useGetUserLLMConfigs(spaceId);
  const { data: globalConfigs, isLoading: globalLoading } = useGetGlobalLLMConfigs();
  const { data: currentConfig, isLoading: currentLoading } = useGetCurrentLLMConfig(spaceId);
  const { mutateAsync: updateCurrent } = useUpdateCurrentLLMConfig(spaceId);

  const handleSelectConfig = async (config: LLMConfigRead | GlobalLLMConfigRead) => {
    await updateCurrent(config.id);
  };

  const handleEditConfig = (config: LLMConfigRead | GlobalLLMConfigRead, isGlobal: boolean) => {
    // Open config editor (to be implemented)
    console.log("Edit config:", config);
  };

  const handleAddNew = () => {
    // Open config creator (to be implemented)
    console.log("Add new config");
  };

  return (
    <div>
      <ChatHeader
        spaceId={spaceId}
        userConfigs={userConfigs}
        globalConfigs={globalConfigs}
        currentConfig={currentConfig}
        isLoading={userLoading || globalLoading || currentLoading}
        onSelectConfig={handleSelectConfig}
        onEditConfig={handleEditConfig}
        onAddNewConfig={handleAddNew}
      />
      {/* Chat content */}
    </div>
  );
}
```

**验收标准：**
- [ ] 用户配置正确加载
- [ ] 全局配置正确加载
- [ ] 当前配置正确显示
- [ ] 切换配置成功保存
- [ ] 错误处理正常（toast 提示）
- [ ] 加载状态正确显示

### 2.3 Spaces/Documents 集成

#### 集成任务 2.3.1: DashboardBreadcrumb 完善

**目标：** 连接真实的 Spaces API，动态显示空间名称

**实现步骤：**

1. **检查现有 Spaces API**
```typescript
// Check existing spaces queries
import { useGetSpacesQuery } from "@/controllers/API/queries/spaces";
```

2. **更新 Breadcrumb 组件**
```typescript
// In dashboard-breadcrumb.tsx
import { useGetSpacesQuery } from "@/controllers/API/queries/spaces";

export function DashboardBreadcrumb() {
  const location = useLocation();
  const pathname = location.pathname;
  const segments = pathname.split("/").filter(Boolean);
  const spaceId = segments[0] === "spaces" && segments[1] ? segments[1] : null;

  // Replace placeholder with real API call
  const { data: spaces } = useGetSpacesQuery({});
  const space = spaces?.find((s) => s.id === Number(spaceId));

  // Use real space name
  const spaceLabel = space?.name || `Space ${spaceId}`;

  // ... rest of implementation
}
```

**验收标准：**
- [ ] 真实空间名称显示
- [ ] 空间切换后面包屑更新
- [ ] 未找到空间时显示 fallback

#### 集成任务 2.3.2: DocumentViewer 集成

**目标：** 连接文档 API，支持查看文档内容

**实现步骤：**

1. **创建文档查询 Hook**
```typescript
// src/controllers/API/queries/documents/use-get-document.ts
export function useGetDocument(documentId: string) {
  return useQuery({
    queryKey: ["documents", documentId],
    queryFn: async () => {
      const response = await api.get(`/documents/${documentId}`);
      return response.data;
    },
    enabled: !!documentId,
  });
}
```

2. **使用 DocumentViewer**
```typescript
import { DocumentViewer } from "@/components/document-viewer";
import { useGetDocument } from "@/controllers/API/queries/documents";

function DocumentItem({ documentId }: { documentId: string }) {
  const { data: document } = useGetDocument(documentId);

  return (
    <DocumentViewer
      title={document?.title || "Document"}
      content={document?.content || ""}
    />
  );
}
```

**验收标准：**
- [ ] 文档内容正确加载
- [ ] Markdown 正确渲染
- [ ] 加载状态正确显示
- [ ] 错误处理正常

---

## 🚀 阶段 3：性能优化与最佳实践（Week 4）

### 3.1 代码分割和懒加载

#### 任务 3.1.1: 大组件懒加载

**优化目标：**
- BlockNoteEditor 已使用 React.lazy ✅
- Thread 组件应懒加载
- ModelConfigSidebar（待迁移）应懒加载

**实现示例：**
```typescript
// src/components/assistant-ui/index.ts
import { lazy } from "react";

// Lazy load large components
export const Thread = lazy(() => import("./thread").then(m => ({ default: m.Thread })));
export const ThreadList = lazy(() => import("./thread-list").then(m => ({ default: m.ThreadList })));

// Export smaller components normally
export { Attachment } from "./attachment";
export { MarkdownText } from "./markdown-text";
```

**使用示例：**
```typescript
import { Suspense } from "react";
import { Thread } from "@/components/assistant-ui";

function ChatPage() {
  return (
    <Suspense fallback={<div>Loading chat...</div>}>
      <Thread />
    </Suspense>
  );
}
```

### 3.2 性能监控

#### 任务 3.2.1: React Query Devtools

**已添加依赖：** `@tanstack/react-query-devtools@^5.90.2` ✅

**启用 Devtools：**
```typescript
// src/App.tsx
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  );
}
```

**监控指标：**
- [ ] 查询缓存命中率
- [ ] 重复请求识别
- [ ] 慢查询识别
- [ ] 内存使用情况

### 3.3 代码质量检查

#### 任务 3.3.1: TypeScript 严格检查

**运行检查：**
```bash
cd src/frontend
npm run type-check  # or tsc --noEmit
```

**修复所有 TypeScript 错误**

#### 任务 3.3.2: ESLint 检查

**运行检查：**
```bash
make lint
```

**修复所有 ESLint 警告**

#### 任务 3.3.3: 格式化

**运行格式化：**
```bash
make format_frontend
```

---

## 📋 测试检查清单

### Phase 1: 基础测试 ✓

- [ ] 所有 UI 组件渲染测试通过
- [ ] Toast 通知系统功能正常
- [ ] Thread 组件基础功能正常
- [ ] Markdown 渲染正确
- [ ] 附件功能正常
- [ ] BlockNote 编辑器正常
- [ ] 语言切换器功能正常
- [ ] 公告横幅功能正常
- [ ] UserDropdown 功能正常
- [ ] 所有工具组件功能正常
- [ ] ModelSelector 显示正常
- [ ] ChatHeader 集成正常
- [ ] DashboardBreadcrumb 路由正确

### Phase 2: 集成测试 ✓

**Thread 功能集成：**
- [ ] 文档提及系统集成完成
- [ ] 线程持久化实现完成
- [ ] 线程列表功能正常

**LLM 配置集成：**
- [ ] LLM Configs API 连接成功
- [ ] 配置列表加载正常
- [ ] 配置切换功能正常
- [ ] 配置创建/编辑功能正常

**Spaces/Documents 集成：**
- [ ] Spaces API 集成完成
- [ ] Documents API 集成完成
- [ ] Breadcrumb 显示真实数据
- [ ] DocumentViewer 加载真实内容

### Phase 3: 优化测试 ✓

- [ ] 代码分割配置正确
- [ ] 懒加载组件正常工作
- [ ] React Query Devtools 可用
- [ ] TypeScript 无错误
- [ ] ESLint 无警告
- [ ] 代码已格式化
- [ ] 打包大小在合理范围
- [ ] 加载性能良好

---

## 🎯 优先级建议

### 立即执行（P0）

1. **基础功能测试** - 确保所有已迁移组件能正常工作
   - 时间估计：2-3 天
   - 阻塞因素：无

2. **LLM 配置集成** - ModelSelector 和 ChatHeader 必须能实际使用
   - 时间估计：2-3 天
   - 阻塞因素：需要后端 API 支持

### 高优先级（P1）

3. **Thread 线程持久化** - 聊天记录需要保存
   - 时间估计：2-3 天
   - 阻塞因素：需要后端 API 支持

4. **Spaces/Documents 集成** - 完善面包屑和文档查看
   - 时间估计：1-2 天
   - 阻塞因素：需要检查现有 API

### 中优先级（P2）

5. **文档提及系统** - 增强聊天功能
   - 时间估计：3-4 天
   - 阻塞因素：依赖 Documents API

6. **性能优化** - 代码分割和懒加载
   - 时间估计：1-2 天
   - 阻塞因素：无

### 低优先级（P3）

7. **其他业务组件迁移** - sidebar、sources、settings 等
   - 时间估计：按需
   - 阻塞因素：依赖相应后端功能

---

## 📝 后续待办事项

### 需要迁移的可选组件

**复杂业务组件（按需迁移）：**
1. model-config-sidebar.tsx - LLM 配置编辑器
2. DocumentsDataTable.tsx - 文档表格（可基于 Langflow table 组件实现）
3. source-detail-panel.tsx - 数据源详情
4. sidebar/* - 侧边栏组件系统（9个文件）
5. sources/* - 数据源管理组件（6个文件）
6. settings/* - 设置管理组件（3个文件）

**这些组件依赖较重，建议在 Langflow 相应功能完善后再迁移。**

### 需要创建的后端 API（如不存在）

1. **Threads API**
   - POST /api/v1/spaces/:spaceId/threads - 创建线程
   - GET /api/v1/spaces/:spaceId/threads - 获取线程列表
   - GET /api/v1/threads/:threadId - 获取线程详情
   - PUT /api/v1/threads/:threadId - 更新线程
   - DELETE /api/v1/threads/:threadId - 删除线程

2. **LLM Configs API**（检查是否已存在）
   - GET /api/v1/spaces/:spaceId/llm-configs - 获取用户配置
   - GET /api/v1/llm-configs/global - 获取全局配置
   - GET /api/v1/spaces/:spaceId/llm-configs/current - 获取当前配置
   - PUT /api/v1/spaces/:spaceId/llm-configs/current - 设置当前配置
   - POST /api/v1/spaces/:spaceId/llm-configs - 创建配置
   - PUT /api/v1/llm-configs/:configId - 更新配置
   - DELETE /api/v1/llm-configs/:configId - 删除配置

3. **Documents Search API**
   - GET /api/v1/spaces/:spaceId/documents/search?q=query - 搜索文档

---

## 📚 参考文档

### 已迁移组件文档

- [SURFSENSE_MIGRATION_REPORT.md](/Users/jiangwei/Python/langflow/SURFSENSE_MIGRATION_REPORT.md) - 完整迁移报告
- [Migration Plan](/Users/jiangwei/.claude/plans/serene-questing-thimble.md) - 原始迁移计划

### Langflow 文档

- Backend API: `src/backend/base/langflow/api/v1/`
- Frontend Types: `src/frontend/src/types/api/`
- React Query Hooks: `src/frontend/src/controllers/API/queries/`
- Stores: `src/frontend/src/stores/`

### 外部依赖文档

- [@assistant-ui/react](https://assistant-ui.com/) - AI 聊天组件
- [BlockNote](https://www.blocknotejs.org/) - 富文本编辑器
- [React Query](https://tanstack.com/query/latest) - 数据获取
- [Zustand](https://zustand-demo.pmnd.rs/) - 状态管理

---

## ✅ 总结

本文档提供了完整的测试和集成路线图：

**测试计划包括：**
- 31 个已迁移组件的功能测试
- UI、AI 聊天、编辑器、工具和业务组件测试用例
- 明确的验收标准

**集成计划包括：**
- Thread 组件文档提及和线程持久化
- LLM 配置系统集成
- Spaces/Documents API 集成
- 性能优化建议

**下一步行动：**
1. 执行 Phase 1 基础测试（2-3 天）
2. 实施 P0/P1 集成任务（4-6 天）
3. 根据需要进行性能优化

**成功标准：**
- 所有测试用例通过 ✅
- 核心功能完全集成 ✅
- 代码质量达标 ✅
- 性能满足要求 ✅
