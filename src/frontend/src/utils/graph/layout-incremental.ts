/**
 * 增量布局算法
 *
 * 用于扩展邻居时，仅对新节点进行布局
 */

import type { GraphEdge, GraphNode } from "@/types/api/graphs";
import { applyForceLayout } from "./layout-force";

/**
 * 增量布局：在现有节点周围放置新节点
 */
export function applyIncrementalLayout(
  allNodes: GraphNode[],
  allEdges: GraphEdge[],
  existingNodes: GraphNode[],
  newNodes: GraphNode[],
  centerNode: GraphNode,
): GraphNode[] {
  // 如果没有新节点，直接返回
  if (newNodes.length === 0) {
    return allNodes;
  }

  // 计算中心节点周围的圆形位置
  const radius = 200; // 新节点距离中心节点的半径
  const angleStep = (2 * Math.PI) / newNodes.length;

  // 初始化新节点的位置（圆形排列）
  const nodesWithInitialPosition = allNodes.map((node) => {
    // 如果是已存在的节点，保持原位置
    const existingNode = existingNodes.find((n) => n.id === node.id);
    if (existingNode) {
      return {
        ...node,
        position: existingNode.position,
      };
    }

    // 如果是新节点，放在中心节点周围
    const index = newNodes.findIndex((n) => n.id === node.id);
    if (index !== -1) {
      const angle = index * angleStep;
      return {
        ...node,
        position: {
          x: centerNode.position.x + radius * Math.cos(angle),
          y: centerNode.position.y + radius * Math.sin(angle),
        },
      };
    }

    return node;
  });

  // 对所有节点运行短时间的 Force 布局（仅 50 次迭代）
  const layoutedNodes = applyForceLayout(nodesWithInitialPosition, allEdges, {
    iterations: 50, // 短时间迭代，避免打乱已有布局
    linkStrength: 0.5,
    chargeStrength: -200,
  });

  return layoutedNodes;
}

/**
 * 固定节点位置的 Force 布局
 *
 * 允许指定某些节点固定不动
 */
export function applyForceLayoutWithFixed(
  nodes: GraphNode[],
  edges: GraphEdge[],
  fixedNodeIds: string[],
): GraphNode[] {
  // TODO: 实现固定节点的 Force 布局
  // 可以通过设置 fx, fy 属性来固定节点
  return nodes;
}
