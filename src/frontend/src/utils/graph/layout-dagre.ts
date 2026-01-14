/**
 * Dagre 层次布局算法
 *
 * 用于树状或层次结构的知识图谱
 */

import dagre from "dagre";
import type { GraphEdge, GraphNode } from "@/types/api/graphs";

export interface DagreLayoutOptions {
  direction: "TB" | "LR" | "BT" | "RL"; // Top-Bottom, Left-Right, etc.
  nodeWidth: number;
  nodeHeight: number;
  rankSep: number; // 层级间距
  nodeSep: number; // 节点间距
  marginX: number;
  marginY: number;
}

const DEFAULT_OPTIONS: DagreLayoutOptions = {
  direction: "TB",
  nodeWidth: 150,
  nodeHeight: 80,
  rankSep: 100,
  nodeSep: 50,
  marginX: 50,
  marginY: 50,
};

/**
 * 计算节点大小（映射 G6 的大小计算）
 */
function calculateNodeSize(degree: number): number {
  // 映射 G6: Math.min(15 + degree * 5, 50)
  const baseSize = 60; // ReactFlow 默认大小
  const sizeIncrement = degree * 10;

  return Math.min(baseSize + sizeIncrement, 150);
}

/**
 * 应用 Dagre 布局
 */
export function applyDagreLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: Partial<DagreLayoutOptions> = {},
): GraphNode[] {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // 创建 dagre 图
  const dagreGraph = new dagre.graphlib.Graph();

  // 设置图配置
  dagreGraph.setGraph({
    rankdir: opts.direction,
    ranksep: opts.rankSep,
    nodesep: opts.nodeSep,
    marginx: opts.marginX,
    marginy: opts.marginY,
  });

  // 设置默认节点和边配置
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // 添加节点到 dagre 图
  nodes.forEach((node) => {
    // 根据 degree 动态调整节点大小
    const size = calculateNodeSize(node.data.degree);

    dagreGraph.setNode(node.id, {
      width: size,
      height: size,
    });
  });

  // 添加边到 dagre 图
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // 计算布局
  dagre.layout(dagreGraph);

  // 更新节点位置
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);

    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWithPosition.width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    };
  });

  return layoutedNodes;
}
