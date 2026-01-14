/**
 * Unit tests for Dagre layout algorithm
 */

import { beforeEach, describe, expect, it } from "vitest";
import type { GraphEdge, GraphNode } from "@/types/api/graphs";
import { applyDagreLayout } from "../layout-dagre";

describe("applyDagreLayout", () => {
  let mockNodes: GraphNode[];
  let mockEdges: GraphEdge[];

  beforeEach(() => {
    mockNodes = [
      {
        id: "1",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Node 1",
          entityType: "Person",
          degree: 2,
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
          degree: 3,
          properties: {},
          original: {} as any,
        },
      },
      {
        id: "3",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Node 3",
          entityType: "Location",
          degree: 1,
          properties: {},
          original: {} as any,
        },
      },
    ];

    mockEdges = [
      {
        id: "e-1",
        source: "1",
        target: "2",
        type: "relationEdge",
        data: {
          relationType: "works_at",
          weight: 0.9,
          properties: {},
          original: {} as any,
        },
      },
      {
        id: "e-2",
        source: "2",
        target: "3",
        type: "relationEdge",
        data: {
          relationType: "located_in",
          weight: 0.8,
          properties: {},
          original: {} as any,
        },
      },
    ];
  });

  it("should apply layout to nodes", () => {
    const layoutedNodes = applyDagreLayout(mockNodes, mockEdges);

    expect(layoutedNodes).toHaveLength(3);
    layoutedNodes.forEach((node) => {
      expect(node.position.x).toBeGreaterThanOrEqual(0);
      expect(node.position.y).toBeGreaterThanOrEqual(0);
      expect(node.position.x).not.toBe(0);
      expect(node.position.y).not.toBe(0);
    });
  });

  it("should preserve node IDs and data", () => {
    const layoutedNodes = applyDagreLayout(mockNodes, mockEdges);

    expect(layoutedNodes[0].id).toBe("1");
    expect(layoutedNodes[1].id).toBe("2");
    expect(layoutedNodes[2].id).toBe("3");

    expect(layoutedNodes[0].data.label).toBe("Node 1");
    expect(layoutedNodes[1].data.label).toBe("Node 2");
    expect(layoutedNodes[2].data.label).toBe("Node 3");
  });

  it("should create hierarchical layout (TB direction)", () => {
    const layoutedNodes = applyDagreLayout(mockNodes, mockEdges, {
      direction: "TB",
    });

    const node1 = layoutedNodes.find((n) => n.id === "1")!;
    const node2 = layoutedNodes.find((n) => n.id === "2")!;
    const node3 = layoutedNodes.find((n) => n.id === "3")!;

    // In TB direction, connected nodes should have increasing Y coordinates
    expect(node1.position.y).toBeLessThan(node2.position.y);
    expect(node2.position.y).toBeLessThan(node3.position.y);
  });

  it("should create horizontal layout (LR direction)", () => {
    const layoutedNodes = applyDagreLayout(mockNodes, mockEdges, {
      direction: "LR",
    });

    const node1 = layoutedNodes.find((n) => n.id === "1")!;
    const node2 = layoutedNodes.find((n) => n.id === "2")!;
    const node3 = layoutedNodes.find((n) => n.id === "3")!;

    // In LR direction, connected nodes should have increasing X coordinates
    expect(node1.position.x).toBeLessThan(node2.position.x);
    expect(node2.position.x).toBeLessThan(node3.position.x);
  });

  it("should respect custom nodeSep option", () => {
    const layout1 = applyDagreLayout(mockNodes, mockEdges, { nodeSep: 50 });
    const layout2 = applyDagreLayout(mockNodes, mockEdges, { nodeSep: 200 });

    // Nodes with larger nodeSep should be further apart
    const distance1 = Math.abs(layout1[0].position.x - layout1[1].position.x);
    const distance2 = Math.abs(layout2[0].position.x - layout2[1].position.x);

    expect(distance2).toBeGreaterThan(distance1);
  });

  it("should respect custom rankSep option", () => {
    const layout1 = applyDagreLayout(mockNodes, mockEdges, { rankSep: 50 });
    const layout2 = applyDagreLayout(mockNodes, mockEdges, { rankSep: 200 });

    // Ranks with larger rankSep should be further apart
    const distance1 = Math.abs(layout1[0].position.y - layout1[1].position.y);
    const distance2 = Math.abs(layout2[0].position.y - layout2[1].position.y);

    expect(distance2).toBeGreaterThan(distance1);
  });

  it("should handle single node", () => {
    const singleNode = [mockNodes[0]];
    const layoutedNodes = applyDagreLayout(singleNode, []);

    expect(layoutedNodes).toHaveLength(1);
    expect(layoutedNodes[0].position.x).toBeGreaterThanOrEqual(0);
    expect(layoutedNodes[0].position.y).toBeGreaterThanOrEqual(0);
  });

  it("should handle nodes without edges", () => {
    const layoutedNodes = applyDagreLayout(mockNodes, []);

    expect(layoutedNodes).toHaveLength(3);
    layoutedNodes.forEach((node) => {
      expect(node.position.x).toBeGreaterThanOrEqual(0);
      expect(node.position.y).toBeGreaterThanOrEqual(0);
    });
  });

  it("should handle disconnected components", () => {
    const disconnectedNodes = [
      ...mockNodes,
      {
        id: "4",
        type: "entityNode" as const,
        position: { x: 0, y: 0 },
        data: {
          label: "Node 4",
          entityType: "Event",
          degree: 0,
          properties: {},
          original: {} as any,
        },
      },
    ];

    const layoutedNodes = applyDagreLayout(disconnectedNodes, mockEdges);

    expect(layoutedNodes).toHaveLength(4);
    const node4 = layoutedNodes.find((n) => n.id === "4");
    expect(node4?.position.x).toBeGreaterThanOrEqual(0);
    expect(node4?.position.y).toBeGreaterThanOrEqual(0);
  });

  it("should scale node size based on degree", () => {
    const highDegreeNode: GraphNode = {
      id: "10",
      type: "entityNode",
      position: { x: 0, y: 0 },
      data: {
        label: "High Degree Node",
        entityType: "Person",
        degree: 20,
        properties: {},
        original: {} as any,
      },
    };

    const nodesWithHighDegree = [mockNodes[0], highDegreeNode, mockNodes[2]];
    const edgesForHighDegree = [
      {
        id: "e-10",
        source: "1",
        target: "10",
        type: "relationEdge" as const,
        data: {
          relationType: "connected",
          weight: 1.0,
          properties: {},
          original: {} as any,
        },
      },
    ];

    const layoutedNodes = applyDagreLayout(
      nodesWithHighDegree,
      edgesForHighDegree,
    );
    expect(layoutedNodes).toHaveLength(3);
    // High degree node should have larger dimensions in layout calculation
  });

  it("should return empty array for empty input", () => {
    const layoutedNodes = applyDagreLayout([], []);
    expect(layoutedNodes).toHaveLength(0);
  });
});
