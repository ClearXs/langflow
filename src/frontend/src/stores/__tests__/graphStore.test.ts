/**
 * Unit tests for Graph Zustand Store
 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { GraphEdge, GraphNode } from "@/types/api/graphs";
import { useGraphStore } from "../graphStore";

describe("useGraphStore", () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useGraphStore());
    act(() => {
      result.current.reset();
    });
  });

  describe("initial state", () => {
    it("should have empty nodes and edges initially", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.nodes).toEqual([]);
      expect(result.current.edges).toEqual([]);
    });

    it("should have no selected node or edge initially", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.selectedNode).toBeNull();
      expect(result.current.selectedEdge).toBeNull();
    });

    it("should have empty selected entity IDs", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.selectedEntityIds).toEqual([]);
    });

    it("should have detail and stats panels hidden initially", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.showDetailPanel).toBe(false);
      expect(result.current.showStatsPanel).toBe(false);
    });

    it("should have force layout as default", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.layoutType).toBe("force");
    });

    it("should have empty filters initially", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.filters).toEqual({
        entityTypes: [],
        relationTypes: [],
        minWeight: 0,
        maxWeight: 1,
        searchQuery: "",
      });
    });

    it("should have empty highlighted nodes", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.highlightedNodeIds).toEqual(new Set());
    });
  });

  describe("setNodes", () => {
    it("should set nodes", () => {
      const { result } = renderHook(() => useGraphStore());
      const mockNodes: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 100, y: 200 },
          data: {
            label: "Test Node",
            entityType: "Person",
            degree: 5,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(mockNodes);
      });

      expect(result.current.nodes).toEqual(mockNodes);
      expect(result.current.nodes).toHaveLength(1);
    });

    it("should replace existing nodes", () => {
      const { result } = renderHook(() => useGraphStore());

      const nodes1: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 1",
            entityType: "Person",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      const nodes2: GraphNode[] = [
        {
          id: "2",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 2",
            entityType: "Organization",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(nodes1);
      });
      expect(result.current.nodes).toHaveLength(1);

      act(() => {
        result.current.setNodes(nodes2);
      });
      expect(result.current.nodes).toHaveLength(1);
      expect(result.current.nodes[0].id).toBe("2");
    });
  });

  describe("addNodes", () => {
    it("should add new nodes to existing nodes", () => {
      const { result } = renderHook(() => useGraphStore());

      const initialNodes: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 1",
            entityType: "Person",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      const newNodes: GraphNode[] = [
        {
          id: "2",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 2",
            entityType: "Organization",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(initialNodes);
      });
      expect(result.current.nodes).toHaveLength(1);

      act(() => {
        result.current.addNodes(newNodes);
      });
      expect(result.current.nodes).toHaveLength(2);
      expect(result.current.nodes.find((n) => n.id === "2")).toBeDefined();
    });

    it("should not add duplicate nodes", () => {
      const { result } = renderHook(() => useGraphStore());

      const initialNodes: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 1",
            entityType: "Person",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(initialNodes);
        result.current.addNodes(initialNodes);
      });

      expect(result.current.nodes).toHaveLength(1);
    });
  });

  describe("selectNode", () => {
    it("should select a node", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNode: GraphNode = {
        id: "1",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Test Node",
          entityType: "Person",
          degree: 5,
          properties: {},
          original: {} as any,
        },
      };

      act(() => {
        result.current.selectNode(mockNode);
      });

      expect(result.current.selectedNode).toEqual(mockNode);
      expect(result.current.showDetailPanel).toBe(true);
    });

    it("should deselect node when null is passed", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNode: GraphNode = {
        id: "1",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Test Node",
          entityType: "Person",
          degree: 5,
          properties: {},
          original: {} as any,
        },
      };

      act(() => {
        result.current.selectNode(mockNode);
      });
      expect(result.current.selectedNode).toEqual(mockNode);

      act(() => {
        result.current.selectNode(null);
      });
      expect(result.current.selectedNode).toBeNull();
      expect(result.current.showDetailPanel).toBe(false);
    });

    it("should clear selected edge when selecting node", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNode: GraphNode = {
        id: "1",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Node",
          entityType: "Person",
          degree: 0,
          properties: {},
          original: {} as any,
        },
      };

      const mockEdge: GraphEdge = {
        id: "e-1",
        source: "1",
        target: "2",
        type: "relationEdge",
        data: {
          relationType: "connected",
          weight: 1.0,
          properties: {},
          original: {} as any,
        },
      };

      act(() => {
        result.current.selectEdge(mockEdge);
      });
      expect(result.current.selectedEdge).toEqual(mockEdge);

      act(() => {
        result.current.selectNode(mockNode);
      });
      expect(result.current.selectedEdge).toBeNull();
    });
  });

  describe("setLayoutType", () => {
    it("should change layout type", () => {
      const { result } = renderHook(() => useGraphStore());

      expect(result.current.layoutType).toBe("force");

      act(() => {
        result.current.setLayoutType("dagre");
      });
      expect(result.current.layoutType).toBe("dagre");
    });
  });

  describe("setFilters", () => {
    it("should update filters", () => {
      const { result } = renderHook(() => useGraphStore());

      act(() => {
        result.current.setFilters({
          entityTypes: ["Person", "Organization"],
          minWeight: 0.5,
        });
      });

      expect(result.current.filters.entityTypes).toEqual([
        "Person",
        "Organization",
      ]);
      expect(result.current.filters.minWeight).toBe(0.5);
      expect(result.current.filters.maxWeight).toBe(1); // Unchanged
    });

    it("should merge filters with existing state", () => {
      const { result } = renderHook(() => useGraphStore());

      act(() => {
        result.current.setFilters({ entityTypes: ["Person"] });
      });
      expect(result.current.filters.entityTypes).toEqual(["Person"]);

      act(() => {
        result.current.setFilters({ relationTypes: ["works_at"] });
      });
      expect(result.current.filters.entityTypes).toEqual(["Person"]);
      expect(result.current.filters.relationTypes).toEqual(["works_at"]);
    });
  });

  describe("highlightNodes", () => {
    it("should highlight specified nodes", () => {
      const { result } = renderHook(() => useGraphStore());

      act(() => {
        result.current.highlightNodes(["1", "2", "3"]);
      });

      expect(result.current.highlightedNodeIds).toEqual(
        new Set(["1", "2", "3"]),
      );
    });

    it("should replace previous highlights", () => {
      const { result } = renderHook(() => useGraphStore());

      act(() => {
        result.current.highlightNodes(["1", "2"]);
      });
      expect(result.current.highlightedNodeIds).toEqual(new Set(["1", "2"]));

      act(() => {
        result.current.highlightNodes(["3", "4"]);
      });
      expect(result.current.highlightedNodeIds).toEqual(new Set(["3", "4"]));
    });

    it("should clear highlights with empty array", () => {
      const { result } = renderHook(() => useGraphStore());

      act(() => {
        result.current.highlightNodes(["1", "2"]);
      });
      expect(result.current.highlightedNodeIds.size).toBe(2);

      act(() => {
        result.current.highlightNodes([]);
      });
      expect(result.current.highlightedNodeIds.size).toBe(0);
    });
  });

  describe("removeNode", () => {
    it("should remove node by ID", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNodes: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 1",
            entityType: "Person",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
        {
          id: "2",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node 2",
            entityType: "Organization",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(mockNodes);
      });
      expect(result.current.nodes).toHaveLength(2);

      act(() => {
        result.current.removeNode("1");
      });
      expect(result.current.nodes).toHaveLength(1);
      expect(result.current.nodes[0].id).toBe("2");
    });

    it("should clear selected node if removed", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNode: GraphNode = {
        id: "1",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Node 1",
          entityType: "Person",
          degree: 0,
          properties: {},
          original: {} as any,
        },
      };

      act(() => {
        result.current.setNodes([mockNode]);
        result.current.selectNode(mockNode);
      });
      expect(result.current.selectedNode).toEqual(mockNode);

      act(() => {
        result.current.removeNode("1");
      });
      expect(result.current.selectedNode).toBeNull();
    });
  });

  describe("reset", () => {
    it("should reset store to initial state", () => {
      const { result } = renderHook(() => useGraphStore());

      const mockNodes: GraphNode[] = [
        {
          id: "1",
          type: "entityNode",
          position: { x: 0, y: 0 },
          data: {
            label: "Node",
            entityType: "Person",
            degree: 0,
            properties: {},
            original: {} as any,
          },
        },
      ];

      act(() => {
        result.current.setNodes(mockNodes);
        result.current.setLayoutType("dagre");
        result.current.setFilters({ entityTypes: ["Person"] });
        result.current.highlightNodes(["1"]);
      });

      expect(result.current.nodes).toHaveLength(1);
      expect(result.current.layoutType).toBe("dagre");

      act(() => {
        result.current.reset();
      });

      expect(result.current.nodes).toEqual([]);
      expect(result.current.edges).toEqual([]);
      expect(result.current.selectedNode).toBeNull();
      expect(result.current.layoutType).toBe("force");
      expect(result.current.filters).toEqual({
        entityTypes: [],
        relationTypes: [],
        minWeight: 0,
        maxWeight: 1,
        searchQuery: "",
      });
      expect(result.current.highlightedNodeIds.size).toBe(0);
    });
  });
});
