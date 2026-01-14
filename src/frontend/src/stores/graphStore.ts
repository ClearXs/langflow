/**
 * Graph Store
 *
 * 使用 Zustand 管理知识图谱状态
 *
 * 功能：
 * - 管理节点和边
 * - 选中状态
 * - 过滤器
 * - 布局配置
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type {
  GraphEdge,
  GraphFilters,
  GraphNode,
  LayoutType,
} from "@/types/api/graphs";

interface GraphState {
  // ========== 核心数据 ==========
  nodes: GraphNode[];
  edges: GraphEdge[];

  // ========== 选中状态 ==========
  selectedNode: GraphNode | null;
  selectedEdge: GraphEdge | null;
  selectedEntityIds: number[]; // 用于子图查询

  // ========== UI 状态 ==========
  showDetailPanel: boolean;
  showStatsPanel: boolean;

  // ========== 布局配置 ==========
  layoutType: LayoutType;

  // ========== 过滤器 ==========
  filters: GraphFilters;

  // ========== 高亮状态 ==========
  highlightedNodeIds: Set<string>;

  // ========== Actions ==========

  // 设置节点和边
  setNodes: (nodes: GraphNode[]) => void;
  setEdges: (edges: GraphEdge[]) => void;

  // 添加节点和边（用于增量更新）
  addNodes: (nodes: GraphNode[]) => void;
  addEdges: (edges: GraphEdge[]) => void;

  // 更新节点（用于拖拽后位置更新）
  updateNode: (nodeId: string, updates: Partial<GraphNode>) => void;

  // 删除节点和边
  removeNode: (nodeId: string) => void;
  removeEdge: (edgeId: string) => void;

  // 选中状态
  selectNode: (node: GraphNode | null) => void;
  selectEdge: (edge: GraphEdge | null) => void;
  setSelectedEntityIds: (ids: number[]) => void;

  // UI 状态
  toggleDetailPanel: () => void;
  toggleStatsPanel: () => void;

  // 布局
  setLayoutType: (type: LayoutType) => void;

  // 过滤器
  setFilters: (filters: Partial<GraphFilters>) => void;
  resetFilters: () => void;

  // 高亮
  highlightNodes: (nodeIds: string[]) => void;
  clearHighlight: () => void;

  // 重置所有状态
  reset: () => void;
}

const initialFilters: GraphFilters = {
  entityTypes: [],
  relationTypes: [],
  minWeight: 0,
  maxWeight: 1,
  searchQuery: "",
};

export const useGraphStore = create<GraphState>()(
  devtools(
    (set, get) => ({
      // ========== 初始状态 ==========
      nodes: [],
      edges: [],
      selectedNode: null,
      selectedEdge: null,
      selectedEntityIds: [],
      showDetailPanel: false,
      showStatsPanel: true,
      layoutType: "force",
      filters: initialFilters,
      highlightedNodeIds: new Set(),

      // ========== Actions 实现 ==========

      setNodes: (nodes) => set({ nodes }),

      setEdges: (edges) => set({ edges }),

      addNodes: (newNodes) =>
        set((state) => {
          const existingIds = new Set(state.nodes.map((n) => n.id));
          const uniqueNewNodes = newNodes.filter((n) => !existingIds.has(n.id));
          return { nodes: [...state.nodes, ...uniqueNewNodes] };
        }),

      addEdges: (newEdges) =>
        set((state) => {
          const existingIds = new Set(state.edges.map((e) => e.id));
          const uniqueNewEdges = newEdges.filter((e) => !existingIds.has(e.id));
          return { edges: [...state.edges, ...uniqueNewEdges] };
        }),

      updateNode: (nodeId, updates) =>
        set((state) => ({
          nodes: state.nodes.map((node) =>
            node.id === nodeId ? { ...node, ...updates } : node,
          ),
        })),

      removeNode: (nodeId) =>
        set((state) => ({
          nodes: state.nodes.filter((n) => n.id !== nodeId),
          edges: state.edges.filter(
            (e) => e.source !== nodeId && e.target !== nodeId,
          ),
          selectedNode:
            state.selectedNode?.id === nodeId ? null : state.selectedNode,
        })),

      removeEdge: (edgeId) =>
        set((state) => ({
          edges: state.edges.filter((e) => e.id !== edgeId),
          selectedEdge:
            state.selectedEdge?.id === edgeId ? null : state.selectedEdge,
        })),

      selectNode: (node) =>
        set({
          selectedNode: node,
          selectedEdge: null,
          showDetailPanel: !!node,
        }),

      selectEdge: (edge) =>
        set({
          selectedEdge: edge,
          selectedNode: null,
        }),

      setSelectedEntityIds: (ids) => set({ selectedEntityIds: ids }),

      toggleDetailPanel: () =>
        set((state) => ({
          showDetailPanel: !state.showDetailPanel,
        })),

      toggleStatsPanel: () =>
        set((state) => ({
          showStatsPanel: !state.showStatsPanel,
        })),

      setLayoutType: (type) => set({ layoutType: type }),

      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        })),

      resetFilters: () => set({ filters: initialFilters }),

      highlightNodes: (nodeIds) =>
        set({
          highlightedNodeIds: new Set(nodeIds),
        }),

      clearHighlight: () =>
        set({
          highlightedNodeIds: new Set(),
        }),

      reset: () =>
        set({
          nodes: [],
          edges: [],
          selectedNode: null,
          selectedEdge: null,
          selectedEntityIds: [],
          showDetailPanel: false,
          showStatsPanel: true,
          layoutType: "force",
          filters: initialFilters,
          highlightedNodeIds: new Set(),
        }),
    }),
    { name: "GraphStore" },
  ),
);
