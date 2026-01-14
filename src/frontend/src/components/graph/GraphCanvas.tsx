/**
 * 图谱画布组件
 *
 * 集成 ReactFlow 和所有交互功能
 */

import ReactFlow, {
  Background,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { useCallback, useEffect } from "react";
import "@xyflow/react/dist/style.css";

import { useGraphStore } from "@/stores/graphStore";
import type { GraphEdge, GraphNode } from "@/types/api/graphs";
import { getEntityTypeColor } from "@/utils/graph/colors";
import { edgeTypes, nodeTypes } from "./node-types";

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
}

export function GraphCanvas({
  nodes: initialNodes,
  edges: initialEdges,
  onNodeClick,
  onEdgeClick,
}: GraphCanvasProps) {
  const { selectNode, selectEdge, updateNode } = useGraphStore();

  const [nodes, setNodes, onNodesChange] =
    useNodesState<GraphNode>(initialNodes);
  const [edges, setEdges, onEdgesChange] =
    useEdgesState<GraphEdge>(initialEdges);

  // 同步外部节点和边的变化
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // 节点点击事件
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const graphNode = node as GraphNode;
      selectNode(graphNode);
      onNodeClick?.(graphNode);
    },
    [selectNode, onNodeClick],
  );

  // 边点击事件
  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const graphEdge = edge as GraphEdge;
      selectEdge(graphEdge);
      onEdgeClick?.(graphEdge);
    },
    [selectEdge, onEdgeClick],
  );

  // 画布点击事件（取消选中）
  const handlePaneClick = useCallback(() => {
    selectNode(null);
    selectEdge(null);
  }, [selectNode, selectEdge]);

  // 节点拖拽结束事件（保存新位置）
  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      updateNode(node.id, { position: node.position });
    },
    [updateNode],
  );

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
          type: "relationEdge",
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
        <Background color="#e5e7eb" gap={16} size={1} />

        {/* 小地图 */}
        <MiniMap
          nodeColor={(node) => {
            const graphNode = node as GraphNode;
            return getEntityTypeColor(graphNode.data.entityType);
          }}
          position="bottom-left"
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  );
}
