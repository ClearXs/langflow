# Yuxi-Know 知识图谱组件完整实现指南

> 所有 React 组件的完整实现代码

**关联文档：**
- [完整迁移计划](./YUXI_KNOW_FRONTEND_MIGRATION_PLAN.md)
- [实施清单](./YUXI_KNOW_GRAPH_MIGRATION_CHECKLIST.md)
- [实施指南](./YUXI_KNOW_GRAPH_IMPLEMENTATION_GUIDE.md)
- [布局算法指南](./YUXI_KNOW_GRAPH_LAYOUT_GUIDE.md)

---

## 目录

1. [工具栏组件](#工具栏组件)
2. [搜索栏组件](#搜索栏组件)
3. [过滤器组件](#过滤器组件)
4. [详情面板组件](#详情面板组件)
5. [统计面板组件](#统计面板组件)
6. [主页面组件](#主页面组件)
7. [路由配置](#路由配置)

---

## 工具栏组件

### 文件：`src/frontend/src/components/graph/GraphToolbar.tsx`

```tsx
/**
 * 图谱工具栏组件
 *
 * 功能：
 * - 缩放控制
 * - 自适应视图
 * - 布局切换
 * - 导出图片
 * - 刷新数据
 */

import { useCallback } from 'react'
import { useReactFlow } from '@xyflow/react'
import {
  ZoomIn,
  ZoomOut,
  Maximize,
  Download,
  RefreshCw,
  Layout,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useGraphStore } from '@/stores/graphStore'
import { useToast } from '@/components/ui/use-toast'
import type { LayoutType } from '@/types/api/graphs'

interface GraphToolbarProps {
  onRefresh?: () => void
  onLayoutChange?: (layout: LayoutType) => void
}

export function GraphToolbar({ onRefresh, onLayoutChange }: GraphToolbarProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  const { layoutType, setLayoutType } = useGraphStore()
  const { toast } = useToast()

  // 放大
  const handleZoomIn = useCallback(() => {
    zoomIn({ duration: 300 })
  }, [zoomIn])

  // 缩小
  const handleZoomOut = useCallback(() => {
    zoomOut({ duration: 300 })
  }, [zoomOut])

  // 自适应视图
  const handleFitView = useCallback(() => {
    fitView({ duration: 300, padding: 0.2 })
  }, [fitView])

  // 切换布局
  const handleLayoutChange = useCallback(
    (layout: LayoutType) => {
      setLayoutType(layout)
      onLayoutChange?.(layout)

      toast({
        title: 'Layout Changed',
        description: `Switched to ${layout} layout`,
      })
    },
    [setLayoutType, onLayoutChange, toast]
  )

  // 导出图片
  const handleExportImage = useCallback(() => {
    // TODO: 实现导出图片功能
    // 可以使用 html-to-image 或 dom-to-image 库

    toast({
      title: 'Export',
      description: 'Export feature coming soon...',
    })
  }, [toast])

  // 刷新数据
  const handleRefresh = useCallback(() => {
    onRefresh?.()

    toast({
      title: 'Refreshing',
      description: 'Reloading graph data...',
    })
  }, [onRefresh, toast])

  return (
    <div className="flex items-center gap-2">
      {/* 缩放控制 */}
      <div className="flex items-center gap-1 border rounded-md">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleZoomIn}
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={handleZoomOut}
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={handleFitView}
          title="Fit View"
        >
          <Maximize className="h-4 w-4" />
        </Button>
      </div>

      {/* 布局切换 */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            <Layout className="h-4 w-4 mr-2" />
            Layout: {layoutType}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={() => handleLayoutChange('force')}>
            Force Layout (G6 Style)
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleLayoutChange('dagre')}>
            Dagre Layout (Hierarchical)
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* 导出图片 */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleExportImage}
      >
        <Download className="h-4 w-4 mr-2" />
        Export
      </Button>

      {/* 刷新 */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleRefresh}
      >
        <RefreshCw className="h-4 w-4 mr-2" />
        Refresh
      </Button>
    </div>
  )
}
```

---

## 搜索栏组件

### 文件：`src/frontend/src/components/graph/GraphSearchBar.tsx`

```tsx
/**
 * 图谱搜索栏组件
 *
 * 功能：
 * - 实时搜索实体
 * - 显示搜索结果下拉列表
 * - 选中实体后更新图谱
 * - 高亮搜索关键词
 */

import { useState, useCallback, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from '@/components/ui/command'
import { Badge } from '@/components/ui/badge'
import { useGetEntitiesQuery } from '@/controllers/API/queries/graphs'
import { useGraphStore } from '@/stores/graphStore'
import { useDebounce } from '@/hooks/use-debounce'

export function GraphSearchBar() {
  const { spaceId } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedQuery = useDebounce(searchQuery, 300)

  const { setSelectedEntityIds, highlightNodes } = useGraphStore()

  // 搜索实体
  const { data: searchResults, isLoading } = useGetEntitiesQuery({
    space_id: Number(spaceId),
    search: debouncedQuery,
    page_size: 10,
  })

  // 选中实体
  const handleSelectEntity = useCallback(
    (entityId: number) => {
      // 更新选中实体，触发子图重新加载
      setSelectedEntityIds([entityId])

      // 高亮匹配节点
      highlightNodes([String(entityId)])

      // 清空搜索
      setSearchQuery('')
    },
    [setSelectedEntityIds, highlightNodes]
  )

  return (
    <Command className="border rounded-md">
      <div className="flex items-center px-3 border-b">
        <Search className="h-4 w-4 mr-2 text-muted-foreground" />
        <CommandInput
          value={searchQuery}
          onValueChange={setSearchQuery}
          placeholder="Search entities..."
          className="border-0 focus:ring-0"
        />
      </div>

      {searchQuery && (
        <CommandList>
          {isLoading && (
            <div className="p-4 text-sm text-muted-foreground">
              Searching...
            </div>
          )}

          {!isLoading && searchResults?.items.length === 0 && (
            <CommandEmpty>No entities found.</CommandEmpty>
          )}

          {!isLoading && searchResults && searchResults.items.length > 0 && (
            <CommandGroup heading="Entities">
              {searchResults.items.map(entity => (
                <CommandItem
                  key={entity.id}
                  onSelect={() => handleSelectEntity(entity.id)}
                  className="flex items-center justify-between"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{entity.name}</span>
                    {entity.description && (
                      <span className="text-xs text-muted-foreground truncate max-w-xs">
                        {entity.description}
                      </span>
                    )}
                  </div>
                  <Badge variant="secondary">{entity.entity_type}</Badge>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      )}
    </Command>
  )
}
```

---

## 过滤器组件

### 文件：`src/frontend/src/components/graph/GraphFilters.tsx`

```tsx
/**
 * 图谱过滤器组件
 *
 * 功能：
 * - 按实体类型过滤
 * - 按关系类型过滤
 * - 按权重范围过滤
 */

import { useMemo } from 'react'
import { Filter } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Separator } from '@/components/ui/separator'
import { useGraphStore } from '@/stores/graphStore'
import { Badge } from '@/components/ui/badge'

interface GraphFiltersProps {
  availableEntityTypes: string[]
  availableRelationTypes: string[]
}

export function GraphFilters({
  availableEntityTypes,
  availableRelationTypes,
}: GraphFiltersProps) {
  const { filters, setFilters, resetFilters } = useGraphStore()

  // 计算已应用的过滤器数量
  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.entityTypes.length > 0) count++
    if (filters.relationTypes.length > 0) count++
    if (filters.minWeight !== 0 || filters.maxWeight !== 1) count++
    return count
  }, [filters])

  // 切换实体类型
  const toggleEntityType = (type: string) => {
    const newTypes = filters.entityTypes.includes(type)
      ? filters.entityTypes.filter(t => t !== type)
      : [...filters.entityTypes, type]

    setFilters({ entityTypes: newTypes })
  }

  // 切换关系类型
  const toggleRelationType = (type: string) => {
    const newTypes = filters.relationTypes.includes(type)
      ? filters.relationTypes.filter(t => t !== type)
      : [...filters.relationTypes, type]

    setFilters({ relationTypes: newTypes })
  }

  // 更新权重范围
  const updateWeightRange = (values: number[]) => {
    setFilters({
      minWeight: values[0],
      maxWeight: values[1],
    })
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-2">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80" align="start">
        <div className="space-y-4">
          {/* 标题 */}
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Filters</h4>
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
              >
                Reset
              </Button>
            )}
          </div>

          <Separator />

          {/* 实体类型过滤 */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Entity Types</Label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {availableEntityTypes.map(type => (
                <div key={type} className="flex items-center space-x-2">
                  <Checkbox
                    id={`entity-${type}`}
                    checked={filters.entityTypes.includes(type)}
                    onCheckedChange={() => toggleEntityType(type)}
                  />
                  <label
                    htmlFor={`entity-${type}`}
                    className="text-sm cursor-pointer"
                  >
                    {type}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* 关系类型过滤 */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Relation Types</Label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {availableRelationTypes.map(type => (
                <div key={type} className="flex items-center space-x-2">
                  <Checkbox
                    id={`relation-${type}`}
                    checked={filters.relationTypes.includes(type)}
                    onCheckedChange={() => toggleRelationType(type)}
                  />
                  <label
                    htmlFor={`relation-${type}`}
                    className="text-sm cursor-pointer"
                  >
                    {type}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* 权重范围 */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">
              Relation Weight Range
            </Label>
            <div className="px-2">
              <Slider
                min={0}
                max={1}
                step={0.1}
                value={[filters.minWeight || 0, filters.maxWeight || 1]}
                onValueChange={updateWeightRange}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{(filters.minWeight || 0).toFixed(1)}</span>
              <span>{(filters.maxWeight || 1).toFixed(1)}</span>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
```

---

## 详情面板组件

### 文件：`src/frontend/src/components/graph/GraphDetailPanel.tsx`

```tsx
/**
 * 图谱详情面板组件
 *
 * 功能：
 * - 显示实体详细信息
 * - 扩展邻居节点
 * - Focus 邻居节点
 * - 链接到源文档
 */

import { useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ExternalLink, GitBranch, Focus, FileText } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useGraphStore } from '@/stores/graphStore'
import { useExpandNeighbors } from '@/controllers/API/queries/graphs'
import { useToast } from '@/components/ui/use-toast'
import { getEntityTypeColor } from '@/utils/graph/colors'

export function GraphDetailPanel() {
  const { spaceId } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()

  const {
    selectedNode,
    showDetailPanel,
    toggleDetailPanel,
    nodes,
    edges,
    addNodes,
    addEdges,
    highlightNodes,
  } = useGraphStore()

  const expandNeighbors = useExpandNeighbors()

  // 关闭面板
  const handleClose = useCallback(() => {
    toggleDetailPanel()
  }, [toggleDetailPanel])

  // 扩展邻居
  const handleExpandNeighbors = useCallback(async () => {
    if (!selectedNode) return

    const entityId = Number(selectedNode.id)

    try {
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
          type: 'entityNode' as const,
          position: { x: 0, y: 0 },
          data: {
            label: e.name,
            entityType: e.entity_type,
            description: e.description,
            degree: 0,
            properties: e.properties,
            original: e,
          },
        }))

      // TODO: 应用增量布局算法
      addNodes(newNodes)
      addEdges(
        result.newRelations.map(r => ({
          id: `e-${r.id}`,
          source: String(r.source_entity_id),
          target: String(r.target_entity_id),
          type: 'relationEdge' as const,
          label: r.relation_type,
          data: {
            relationType: r.relation_type,
            weight: r.weight,
            description: r.description,
            properties: r.properties,
            original: r,
          },
        }))
      )

      toast({
        title: 'Neighbors Expanded',
        description: `Added ${newNodes.length} new entities`,
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to expand neighbors',
        variant: 'destructive',
      })
    }
  }, [selectedNode, spaceId, expandNeighbors, nodes, addNodes, addEdges, toast])

  // Focus 邻居
  const handleFocusNeighbors = useCallback(() => {
    if (!selectedNode) return

    // 找出所有相连的节点
    const connectedNodeIds = edges
      .filter(edge =>
        edge.source === selectedNode.id || edge.target === selectedNode.id
      )
      .flatMap(edge => [edge.source, edge.target])
      .filter(id => id !== selectedNode.id)

    // 高亮选中节点和相连节点
    highlightNodes([selectedNode.id, ...connectedNodeIds])

    toast({
      title: 'Focus Neighbors',
      description: `Highlighted ${connectedNodeIds.length} connected entities`,
    })
  }, [selectedNode, edges, highlightNodes, toast])

  // 跳转到源文档
  const handleGoToDocument = useCallback(() => {
    if (!selectedNode?.data.original.document_id) return

    navigate(`/spaces/${spaceId}/documents/${selectedNode.data.original.document_id}`)
  }, [selectedNode, spaceId, navigate])

  if (!selectedNode) return null

  const entity = selectedNode.data.original
  const color = getEntityTypeColor(entity.entity_type)

  return (
    <Sheet open={showDetailPanel} onOpenChange={handleClose}>
      <SheetContent className="w-[400px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            {entity.name}
          </SheetTitle>
          <SheetDescription>
            Entity ID: {entity.id}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6">
          <div className="space-y-6">
            {/* 基本信息 */}
            <div className="space-y-3">
              <div>
                <Label className="text-xs text-muted-foreground">Type</Label>
                <div className="mt-1">
                  <Badge style={{ backgroundColor: color }}>
                    {entity.entity_type}
                  </Badge>
                </div>
              </div>

              {entity.description && (
                <div>
                  <Label className="text-xs text-muted-foreground">Description</Label>
                  <p className="mt-1 text-sm">{entity.description}</p>
                </div>
              )}

              {entity.aliases.length > 0 && (
                <div>
                  <Label className="text-xs text-muted-foreground">Aliases</Label>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {entity.aliases.map((alias, index) => (
                      <Badge key={index} variant="outline">
                        {alias}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <Label className="text-xs text-muted-foreground">Connections</Label>
                <p className="mt-1 text-sm font-medium">
                  {selectedNode.data.degree} relations
                </p>
              </div>
            </div>

            <Separator />

            {/* 操作按钮 */}
            <div className="space-y-2">
              <Button
                className="w-full justify-start"
                variant="outline"
                onClick={handleExpandNeighbors}
                disabled={expandNeighbors.isPending}
              >
                <GitBranch className="h-4 w-4 mr-2" />
                {expandNeighbors.isPending ? 'Expanding...' : 'Expand Neighbors'}
              </Button>

              <Button
                className="w-full justify-start"
                variant="outline"
                onClick={handleFocusNeighbors}
              >
                <Focus className="h-4 w-4 mr-2" />
                Focus Neighbors
              </Button>

              {entity.document_id && (
                <Button
                  className="w-full justify-start"
                  variant="outline"
                  onClick={handleGoToDocument}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  View Source Document
                </Button>
              )}
            </div>

            <Separator />

            {/* 自定义属性 */}
            {Object.keys(entity.properties).length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Properties</Label>
                <div className="space-y-2">
                  {Object.entries(entity.properties).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-start">
                      <span className="text-xs font-medium">{key}:</span>
                      <span className="text-xs text-muted-foreground max-w-[200px] text-right">
                        {JSON.stringify(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Separator />

            {/* 元数据 */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Metadata</Label>
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created:</span>
                  <span>{new Date(entity.created_at).toLocaleDateString()}</span>
                </div>
                {entity.updated_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Updated:</span>
                    <span>{new Date(entity.updated_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
```

---

## 统计面板组件

### 文件：`src/frontend/src/components/graph/GraphStats.tsx`

```tsx
/**
 * 图谱统计面板组件
 *
 * 功能：
 * - 显示实体/关系总数
 * - 实体类型分布
 * - 关系类型分布
 */

import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { BarChart3, Network, TrendingUp } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useGetGraphStatsQuery } from '@/controllers/API/queries/graphs'
import { getEntityTypeColor } from '@/utils/graph/colors'

export function GraphStats() {
  const { spaceId } = useParams()

  const { data: stats, isLoading } = useGetGraphStatsQuery(Number(spaceId))

  // 计算百分比
  const entityTypePercentages = useMemo(() => {
    if (!stats) return []

    const total = stats.entity_count

    return Object.entries(stats.entity_type_distribution)
      .map(([type, count]) => ({
        type,
        count,
        percentage: (count / total) * 100,
        color: getEntityTypeColor(type),
      }))
      .sort((a, b) => b.count - a.count)
  }, [stats])

  const relationTypePercentages = useMemo(() => {
    if (!stats) return []

    const total = stats.relation_count

    return Object.entries(stats.relation_type_distribution)
      .map(([type, count]) => ({
        type,
        count,
        percentage: (count / total) * 100,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)  // 只显示前 5 个
  }, [stats])

  if (isLoading || !stats) {
    return (
      <Card className="absolute bottom-4 right-4 w-80">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Loading statistics...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="absolute bottom-4 right-4 w-80 shadow-lg">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Graph Statistics
        </CardTitle>
        <CardDescription className="text-xs">
          Knowledge graph overview
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 总数 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col">
            <div className="flex items-center gap-2 text-muted-foreground text-xs">
              <Network className="h-3 w-3" />
              Entities
            </div>
            <p className="text-2xl font-bold">{stats.entity_count}</p>
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2 text-muted-foreground text-xs">
              <TrendingUp className="h-3 w-3" />
              Relations
            </div>
            <p className="text-2xl font-bold">{stats.relation_count}</p>
          </div>
        </div>

        {/* 实体类型分布 */}
        <div className="space-y-2">
          <p className="text-xs font-medium">Entity Types</p>
          <div className="space-y-2">
            {entityTypePercentages.map(({ type, count, percentage, color }) => (
              <div key={type} className="space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span>{type}</span>
                  </div>
                  <span className="text-muted-foreground">
                    {count} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <Progress
                  value={percentage}
                  className="h-1"
                  style={{
                    // @ts-ignore
                    '--progress-background': color,
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* 关系类型分布 */}
        <div className="space-y-2">
          <p className="text-xs font-medium">Top Relation Types</p>
          <div className="flex flex-wrap gap-1">
            {relationTypePercentages.map(({ type, count }) => (
              <Badge key={type} variant="outline" className="text-xs">
                {type} ({count})
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## 主页面组件

### 文件：`src/frontend/src/pages/SpaceDetailPage/GraphPage.tsx`

```tsx
/**
 * 知识图谱主页面
 *
 * 集成所有组件，实现完整的图谱功能
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { ReactFlowProvider } from '@xyflow/react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Network, AlertCircle, FileText } from 'lucide-react'

import { GraphCanvas } from '@/components/graph/GraphCanvas'
import { GraphToolbar } from '@/components/graph/GraphToolbar'
import { GraphSearchBar } from '@/components/graph/GraphSearchBar'
import { GraphFilters } from '@/components/graph/GraphFilters'
import { GraphDetailPanel } from '@/components/graph/GraphDetailPanel'
import { GraphStats } from '@/components/graph/GraphStats'

import { useGetEntitiesQuery, useGetSubgraphQuery } from '@/controllers/API/queries/graphs'
import { useGraphStore } from '@/stores/graphStore'
import { transformEntitiesToNodes, transformRelationsToEdges } from '@/utils/graph'
import { applyForceLayout } from '@/utils/graph/layout-force'
import { applyDagreLayout } from '@/utils/graph/layout-dagre'

import type { LayoutType } from '@/types/api/graphs'

export default function GraphPage() {
  const { spaceId } = useParams()
  const { layoutType, selectedEntityIds, filters } = useGraphStore()

  // Step 1: 获取前 20 个实体作为候选
  const { data: entitiesData, isLoading: entitiesLoading, refetch: refetchEntities } = useGetEntitiesQuery({
    space_id: Number(spaceId),
    page: 1,
    page_size: 20,
  })

  // Step 2: 使用选中的实体 ID 或前 10 个实体获取子图
  const startingEntityIds = useMemo(() => {
    if (selectedEntityIds.length > 0) {
      return selectedEntityIds
    }
    return entitiesData?.items.slice(0, 10).map(e => e.id) || []
  }, [entitiesData, selectedEntityIds])

  const {
    data: subgraphData,
    isLoading: subgraphLoading,
    error: subgraphError,
    refetch: refetchSubgraph,
  } = useGetSubgraphQuery(
    Number(spaceId),
    {
      entity_ids: startingEntityIds,
      max_depth: 2,
      max_nodes: 100,
    },
    { enabled: startingEntityIds.length > 0 }
  )

  // Step 3: 转换数据并应用布局
  const { nodes, edges } = useMemo(() => {
    if (!subgraphData) return { nodes: [], edges: [] }

    const transformedNodes = transformEntitiesToNodes(
      subgraphData.entities,
      subgraphData.relations
    )
    const transformedEdges = transformRelationsToEdges(subgraphData.relations)

    // 根据布局类型应用布局算法
    const layoutedNodes = layoutType === 'force'
      ? applyForceLayout(transformedNodes, transformedEdges, {
          width: window.innerWidth,
          height: window.innerHeight - 200,
        })
      : applyDagreLayout(transformedNodes, transformedEdges)

    return { nodes: layoutedNodes, edges: transformedEdges }
  }, [subgraphData, layoutType])

  // 提取所有唯一的实体类型和关系类型
  const { availableEntityTypes, availableRelationTypes } = useMemo(() => {
    const entityTypes = new Set(nodes.map(n => n.data.entityType))
    const relationTypes = new Set(edges.map(e => e.data.relationType))

    return {
      availableEntityTypes: Array.from(entityTypes),
      availableRelationTypes: Array.from(relationTypes),
    }
  }, [nodes, edges])

  // 刷新数据
  const handleRefresh = useCallback(() => {
    refetchEntities()
    refetchSubgraph()
  }, [refetchEntities, refetchSubgraph])

  // 切换布局
  const handleLayoutChange = useCallback((layout: LayoutType) => {
    // 布局会通过 store 更新，触发 useMemo 重新计算
  }, [])

  // Loading 状态
  if (entitiesLoading || subgraphLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <Network className="h-12 w-12 mx-auto text-muted-foreground animate-pulse" />
          <p className="text-sm text-muted-foreground">Loading knowledge graph...</p>
        </div>
      </div>
    )
  }

  // 错误状态
  if (subgraphError) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load knowledge graph. Please try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  // 空状态
  if (!subgraphData || subgraphData.entities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="p-8 text-center max-w-md">
          <div className="flex flex-col items-center gap-4">
            <Network className="h-12 w-12 text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold">No Knowledge Graph Data</h3>
              <p className="text-sm text-muted-foreground mt-2">
                Upload documents to extract entities and build the knowledge graph.
              </p>
            </div>
            <Button onClick={() => window.location.href = `/spaces/${spaceId}/documents`}>
              <FileText className="h-4 w-4 mr-2" />
              Go to Documents
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <ReactFlowProvider>
      <div className="h-full flex flex-col">
        {/* 顶部工具栏 */}
        <div className="flex items-center gap-4 p-4 border-b bg-background">
          <div className="flex-1 max-w-md">
            <GraphSearchBar />
          </div>

          <GraphFilters
            availableEntityTypes={availableEntityTypes}
            availableRelationTypes={availableRelationTypes}
          />

          <GraphToolbar
            onRefresh={handleRefresh}
            onLayoutChange={handleLayoutChange}
          />
        </div>

        {/* 主画布 */}
        <div className="flex-1 relative">
          <GraphCanvas nodes={nodes} edges={edges} />

          {/* 统计面板（右下角） */}
          <GraphStats />
        </div>

        {/* 详情面板（Sheet） */}
        <GraphDetailPanel />
      </div>
    </ReactFlowProvider>
  )
}
```

---

## 路由配置

### 文件：`src/frontend/src/routes.tsx`

```tsx
// 添加 Graph 路由

import GraphPage from '@/pages/SpaceDetailPage/GraphPage'

// 在 SpaceDetailPage 的子路由中添加：
{
  path: 'graph',
  element: <GraphPage />,
}
```

### 在 Space Detail 页面添加 Graph 标签

```tsx
// src/frontend/src/pages/SpaceDetailPage/index.tsx

// 在 Tabs 中添加：
<TabsList>
  <TabsTrigger value="chats">Chats</TabsTrigger>
  <TabsTrigger value="notes">Notes</TabsTrigger>
  <TabsTrigger value="documents">Documents</TabsTrigger>
  <TabsTrigger value="graph">Knowledge Graph</TabsTrigger>  {/* 新增 */}
</TabsList>

<TabsContent value="graph">
  <GraphPage />
</TabsContent>
```

---

## 完整实施步骤

### 第 1 步：安装依赖

```bash
cd src/frontend
npm install @xyflow/react dagre d3-force
npm install @types/dagre --save-dev
```

### 第 2 步：创建文件（按顺序）

```bash
# 1. 类型定义
touch src/types/api/graphs.ts

# 2. Hooks
mkdir -p src/controllers/API/queries/graphs
touch src/controllers/API/queries/graphs/use-get-entities.ts
touch src/controllers/API/queries/graphs/use-get-subgraph.ts
touch src/controllers/API/queries/graphs/use-expand-neighbors.ts
touch src/controllers/API/queries/graphs/use-get-graph-stats.ts
touch src/controllers/API/queries/graphs/index.ts

# 3. Store
touch src/stores/graphStore.ts

# 4. Utils
mkdir -p src/utils/graph
touch src/utils/graph/transform-entities.ts
touch src/utils/graph/transform-relations.ts
touch src/utils/graph/layout-dagre.ts
touch src/utils/graph/layout-force.ts
touch src/utils/graph/layout-incremental.ts
touch src/utils/graph/colors.ts
touch src/utils/graph/index.ts

# 5. Components
mkdir -p src/components/graph
touch src/components/graph/EntityNode.tsx
touch src/components/graph/RelationEdge.tsx
touch src/components/graph/GraphCanvas.tsx
touch src/components/graph/GraphToolbar.tsx
touch src/components/graph/GraphSearchBar.tsx
touch src/components/graph/GraphFilters.tsx
touch src/components/graph/GraphDetailPanel.tsx
touch src/components/graph/GraphStats.tsx
touch src/components/graph/node-types.ts
touch src/components/graph/index.ts

# 6. Page
touch src/pages/SpaceDetailPage/GraphPage.tsx
```

### 第 3 步：复制代码

按照本文档中的代码，依次复制到对应文件。

### 第 4 步：测试

```bash
# 启动后端
make backend

# 启动前端
make frontend

# 访问
http://localhost:3000/spaces/1/graph
```

---

**文档版本：** 1.0
**更新日期：** 2026-01-09
**状态：** ✅ 完整实现指南完成
