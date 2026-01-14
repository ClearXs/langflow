/**
 * D3 Force 力导向布局
 *
 * 映射 G6 的 d3-force 配置，保持视觉一致性
 */

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";

import type { GraphEdge, GraphNode } from "@/types/api/graphs";

export interface ForceLayoutOptions {
  width: number;
  height: number;
  iterations: number;
  linkDistance: number;
  linkStrength: number;
  chargeStrength: number;
  centerStrength: number;
  preventOverlap: boolean;
}

const DEFAULT_OPTIONS: ForceLayoutOptions = {
  width: 1200,
  height: 800,
  iterations: 150, // 映射 G6: iterations: 150
  linkDistance: 100, // 映射 G6: link.distance: 100
  linkStrength: 0.8, // 映射 G6: link.strength: 0.8
  chargeStrength: -400, // 映射 G6: charge.strength: -400
  centerStrength: 0.1, // 映射 G6: center.strength: 0.1
  preventOverlap: true, // 映射 G6: preventOverlap: true
};

interface ForceNode extends SimulationNodeDatum {
  id: string;
  degree: number;
  x?: number;
  y?: number;
}

interface ForceLink extends SimulationLinkDatum<ForceNode> {
  source: string | ForceNode;
  target: string | ForceNode;
}

/**
 * 计算节点半径（映射 G6 的大小计算）
 */
function calculateNodeRadius(degree: number): number {
  // 映射 G6: Math.min(15 + degree * 5, 50)
  const size = Math.min(15 + degree * 5, 50);
  return size / 2;
}

/**
 * 应用 D3 Force 布局（映射 G6 配置）
 */
export function applyForceLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: Partial<ForceLayoutOptions> = {},
): GraphNode[] {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // 准备节点数据
  const forceNodes: ForceNode[] = nodes.map((node) => ({
    id: node.id,
    degree: node.data.degree,
    x: node.position.x || opts.width / 2,
    y: node.position.y || opts.height / 2,
  }));

  // 准备边数据
  const forceLinks: ForceLink[] = edges.map((edge) => ({
    source: edge.source,
    target: edge.target,
  }));

  // 创建力导向模拟
  const simulation = forceSimulation(forceNodes)
    // 连接力（映射 G6 link）
    .force(
      "link",
      forceLink(forceLinks)
        .id((d: any) => d.id)
        .distance(opts.linkDistance)
        .strength(opts.linkStrength),
    )

    // 排斥力（映射 G6 charge）
    .force(
      "charge",
      forceManyBody()
        .strength(opts.chargeStrength)
        .distanceMax(600), // 映射 G6: charge.distanceMax: 600
    )

    // 中心力（映射 G6 center）
    .force(
      "center",
      forceCenter(opts.width / 2, opts.height / 2).strength(
        opts.centerStrength,
      ),
    )

    // X/Y 轴力（保持节点在画布内）
    .force("x", forceX(opts.width / 2).strength(0.05))
    .force("y", forceY(opts.height / 2).strength(0.05));

  // 碰撞力（映射 G6 preventOverlap）
  if (opts.preventOverlap) {
    simulation.force(
      "collide",
      forceCollide()
        .radius((d: any) => calculateNodeRadius(d.degree) + 10)
        .strength(0.7),
    );
  }

  // 运行指定次数的迭代
  simulation.tick(opts.iterations);
  simulation.stop();

  // 更新节点位置
  const layoutedNodes = nodes.map((node, index) => {
    const forceNode = forceNodes[index];

    return {
      ...node,
      position: {
        x: forceNode.x || 0,
        y: forceNode.y || 0,
      },
    };
  });

  return layoutedNodes;
}

/**
 * 动画版本的 Force 布局（使用 requestAnimationFrame）
 */
export function applyForceLayoutAnimated(
  nodes: GraphNode[],
  edges: GraphEdge[],
  onTick: (nodes: GraphNode[]) => void,
  options: Partial<ForceLayoutOptions> = {},
): () => void {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // 准备数据
  const forceNodes: ForceNode[] = nodes.map((node) => ({
    id: node.id,
    degree: node.data.degree,
    x: node.position.x || opts.width / 2,
    y: node.position.y || opts.height / 2,
  }));

  const forceLinks: ForceLink[] = edges.map((edge) => ({
    source: edge.source,
    target: edge.target,
  }));

  // 创建模拟
  const simulation = forceSimulation(forceNodes)
    .force(
      "link",
      forceLink(forceLinks)
        .id((d: any) => d.id)
        .distance(opts.linkDistance)
        .strength(opts.linkStrength),
    )
    .force(
      "charge",
      forceManyBody().strength(opts.chargeStrength).distanceMax(600),
    )
    .force(
      "center",
      forceCenter(opts.width / 2, opts.height / 2).strength(
        opts.centerStrength,
      ),
    )
    .force("x", forceX(opts.width / 2).strength(0.05))
    .force("y", forceY(opts.height / 2).strength(0.05));

  if (opts.preventOverlap) {
    simulation.force(
      "collide",
      forceCollide()
        .radius((d: any) => calculateNodeRadius(d.degree) + 10)
        .strength(0.7),
    );
  }

  // 每次 tick 更新节点位置
  simulation.on("tick", () => {
    const layoutedNodes = nodes.map((node, index) => {
      const forceNode = forceNodes[index];

      return {
        ...node,
        position: {
          x: forceNode.x || 0,
          y: forceNode.y || 0,
        },
      };
    });

    onTick(layoutedNodes);
  });

  // 返回停止函数
  return () => {
    simulation.stop();
  };
}
