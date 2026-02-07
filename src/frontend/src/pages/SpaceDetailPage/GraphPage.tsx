/**
 * 知识图谱主页面
 *
 * 集成所有组件，实现完整的图谱功能
 */

import { ReactFlowProvider } from "@xyflow/react";
import { AlertCircle, FileText, Network } from "lucide-react";
import { useEffect, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { NodeDetailsPanel } from "@/components/graph/NodeDetailsPanel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  useGetEntitiesQuery,
  useGetSubgraphQuery,
} from "@/controllers/API/queries/graphs";
import { useGraphStore } from "@/stores/graphStore";
import {
  transformEntitiesToNodes,
  transformGraphNodesToNodes,
  transformRelationsToEdges,
  transformGraphEdgesToEdges,
} from "@/utils/graph";
import { applyDagreLayout } from "@/utils/graph/layout-dagre";
import { applyForceLayout } from "@/utils/graph/layout-force";

export default function GraphPage() {
  const { spaceId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ✅ CORRECT: Use single-value selectors (stable references)
  const layoutType = useGraphStore((state) => state.layoutType);
  const selectedEntityIds = useGraphStore((state) => state.selectedEntityIds);
  const setSelectedEntityIds = useGraphStore((state) => state.setSelectedEntityIds);
  const selectedNode = useGraphStore((state) => state.selectedNode);
  const selectNode = useGraphStore((state) => state.selectNode);

  useEffect(() => {
    const rawIds = searchParams.get("entity_ids");
    if (!rawIds) return;
    const parsed = rawIds
      .split(",")
      .map((value) => parseInt(value.trim(), 10))
      .filter((value) => !Number.isNaN(value));
    if (parsed.length > 0) {
      setSelectedEntityIds(parsed);
    }
  }, [searchParams, setSelectedEntityIds]);

  // Step 1: 获取前 20 个实体作为候选
  const { data: entitiesData, isLoading: entitiesLoading } =
    useGetEntitiesQuery({
      space_id: Number(spaceId),
      page: 1,
      page_size: 20,
    });

  // Step 2: 使用选中的实体 ID 或前 10 个实体获取子图
  const startingEntityIds = useMemo(() => {
    if (selectedEntityIds.length > 0) {
      return selectedEntityIds;
    }
    return entitiesData?.items.slice(0, 10).map((e) => e.id) || [];
  }, [entitiesData, selectedEntityIds]);

  const {
    data: subgraphData,
    isLoading: subgraphLoading,
    error: subgraphError,
  } = useGetSubgraphQuery(
    Number(spaceId),
    {
      entity_ids: startingEntityIds,
      max_depth: 2,
      max_nodes: 100,
    },
    { enabled: startingEntityIds.length > 0 },
  );

  // Step 3: 转换数据并应用布局
  const { nodes, edges } = useMemo(() => {
    if (!subgraphData) return { nodes: [], edges: [] };

    const hasGraphApiShape = "nodes" in subgraphData && "edges" in subgraphData;
    const transformedNodes = hasGraphApiShape
      ? transformGraphNodesToNodes(subgraphData.nodes, subgraphData.edges)
      : transformEntitiesToNodes(subgraphData.entities, subgraphData.relations);
    const transformedEdges = hasGraphApiShape
      ? transformGraphEdgesToEdges(subgraphData.edges)
      : transformRelationsToEdges(subgraphData.relations);

    // 根据布局类型应用布局算法
    const layoutedNodes =
      layoutType === "force"
        ? applyForceLayout(transformedNodes, transformedEdges, {
            width: window.innerWidth,
            height: window.innerHeight - 200,
          })
        : applyDagreLayout(transformedNodes, transformedEdges);

    return { nodes: layoutedNodes, edges: transformedEdges };
  }, [subgraphData, layoutType]);

  // Loading 状态
  if (entitiesLoading || subgraphLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <Network className="h-12 w-12 mx-auto text-muted-foreground animate-pulse" />
          <p className="text-sm text-muted-foreground">
            Loading knowledge graph...
          </p>
        </div>
      </div>
    );
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
    );
  }

  // 空状态（兼容旧结构 entities/relations 与新结构 nodes/edges）
  const isEmptyGraph =
    !subgraphData ||
    ((subgraphData as { nodes?: unknown[] }).nodes?.length ??
      (subgraphData as { entities?: unknown[] }).entities?.length ??
      0) === 0;

  if (isEmptyGraph) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="p-8 text-center max-w-md">
          <div className="flex flex-col items-center gap-4">
            <Network className="h-12 w-12 text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold">No Knowledge Graph Data</h3>
              <p className="text-sm text-muted-foreground mt-2">
                Upload documents to extract entities and build the knowledge
                graph.
              </p>
            </div>
            <Button onClick={() => navigate(`/spaces/${spaceId}/documents`)}>
              <FileText className="h-4 w-4 mr-2" />
              Go to Documents
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className="h-full flex flex-col">
        {/* 主画布 */}
        <div className="flex-1 relative">
          <GraphCanvas nodes={nodes} edges={edges} />

          {/* 节点详情面板 */}
          <NodeDetailsPanel
            node={selectedNode}
            onClose={() => selectNode(null)}
          />
        </div>
      </div>
    </ReactFlowProvider>
  );
}
