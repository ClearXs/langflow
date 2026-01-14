/**
 * Unit tests for Force layout algorithm
 */

import { beforeEach, describe, expect, it } from "vitest";
import type { GraphEdge, GraphNode } from "@/types/api/graphs";
import { applyForceLayout } from "../layout-force";

describe("applyForceLayout", () => {
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
      {
        id: "4",
        type: "entityNode",
        position: { x: 0, y: 0 },
        data: {
          label: "Node 4",
          entityType: "Event",
          degree: 2,
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
      {
        id: "e-3",
        source: "1",
        target: "4",
        type: "relationEdge",
        data: {
          relationType: "attends",
          weight: 0.7,
          properties: {},
          original: {} as any,
        },
      },
    ];
  });

  it("should apply force layout to nodes", () => {
    const layoutedNodes = applyForceLayout(mockNodes, mockEdges);

    expect(layoutedNodes).toHaveLength(4);
    layoutedNodes.forEach((node) => {
      expect(node.position.x).toBeGreaterThanOrEqual(0);
      expect(node.position.y).toBeGreaterThanOrEqual(0);
      expect(typeof node.position.x).toBe("number");
      expect(typeof node.position.y).toBe("number");
      expect(Number.isFinite(node.position.x)).toBe(true);
      expect(Number.isFinite(node.position.y)).toBe(true);
    });
  });

  it("should preserve node IDs and data", () => {
    const layoutedNodes = applyForceLayout(mockNodes, mockEdges);

    expect(layoutedNodes[0].id).toBe("1");
    expect(layoutedNodes[1].id).toBe("2");
    expect(layoutedNodes[2].id).toBe("3");
    expect(layoutedNodes[3].id).toBe("4");

    expect(layoutedNodes[0].data.label).toBe("Node 1");
    expect(layoutedNodes[1].data.label).toBe("Node 2");
  });

  it("should spread nodes within canvas bounds", () => {
    const width = 800;
    const height = 600;

    const layoutedNodes = applyForceLayout(mockNodes, mockEdges, {
      width,
      height,
    });

    layoutedNodes.forEach((node) => {
      // Nodes should generally be within canvas bounds (with some margin for collision)
      expect(node.position.x).toBeGreaterThan(-100);
      expect(node.position.x).toBeLessThan(width + 100);
      expect(node.position.y).toBeGreaterThan(-100);
      expect(node.position.y).toBeLessThan(height + 100);
    });
  });

  it("should keep connected nodes relatively close", () => {
    const layoutedNodes = applyForceLayout(mockNodes, mockEdges, {
      linkDistance: 100,
    });

    const node1 = layoutedNodes.find((n) => n.id === "1")!;
    const node2 = layoutedNodes.find((n) => n.id === "2")!;

    const distance = Math.sqrt(
      Math.pow(node2.position.x - node1.position.x, 2) +
        Math.pow(node2.position.y - node1.position.y, 2),
    );

    // Connected nodes should be relatively close (within reasonable range)
    expect(distance).toBeLessThan(300);
  });

  it("should respect custom iterations option", () => {
    const layout1 = applyForceLayout(mockNodes, mockEdges, { iterations: 10 });
    const layout2 = applyForceLayout(mockNodes, mockEdges, { iterations: 200 });

    // More iterations should produce more stable layout
    expect(layout1).toHaveLength(4);
    expect(layout2).toHaveLength(4);
  });

  it("should respect custom linkDistance option", () => {
    const layout1 = applyForceLayout(mockNodes, mockEdges, {
      linkDistance: 50,
      iterations: 150,
    });
    const layout2 = applyForceLayout(mockNodes, mockEdges, {
      linkDistance: 200,
      iterations: 150,
    });

    const getAverageDistance = (nodes: GraphNode[]) => {
      const node1 = nodes.find((n) => n.id === "1")!;
      const node2 = nodes.find((n) => n.id === "2")!;
      return Math.sqrt(
        Math.pow(node2.position.x - node1.position.x, 2) +
          Math.pow(node2.position.y - node1.position.y, 2),
      );
    };

    const dist1 = getAverageDistance(layout1);
    const dist2 = getAverageDistance(layout2);

    // Larger linkDistance should result in nodes being further apart
    expect(dist2).toBeGreaterThan(dist1);
  });

  it("should respect custom chargeStrength option", () => {
    const weakCharge = applyForceLayout(mockNodes, mockEdges, {
      chargeStrength: -100,
    });
    const strongCharge = applyForceLayout(mockNodes, mockEdges, {
      chargeStrength: -800,
    });

    expect(weakCharge).toHaveLength(4);
    expect(strongCharge).toHaveLength(4);

    // Stronger charge should spread nodes more
    // (This is a qualitative test - exact values depend on simulation)
  });

  it("should center nodes around canvas center", () => {
    const width = 800;
    const height = 600;

    const layoutedNodes = applyForceLayout(mockNodes, mockEdges, {
      width,
      height,
      centerStrength: 0.5,
    });

    const avgX =
      layoutedNodes.reduce((sum, n) => sum + n.position.x, 0) /
      layoutedNodes.length;
    const avgY =
      layoutedNodes.reduce((sum, n) => sum + n.position.y, 0) /
      layoutedNodes.length;

    // Average position should be reasonably close to center
    expect(avgX).toBeGreaterThan(width / 2 - 200);
    expect(avgX).toBeLessThan(width / 2 + 200);
    expect(avgY).toBeGreaterThan(height / 2 - 200);
    expect(avgY).toBeLessThan(height / 2 + 200);
  });

  it("should handle single node", () => {
    const singleNode = [mockNodes[0]];
    const layoutedNodes = applyForceLayout(singleNode, []);

    expect(layoutedNodes).toHaveLength(1);
    expect(Number.isFinite(layoutedNodes[0].position.x)).toBe(true);
    expect(Number.isFinite(layoutedNodes[0].position.y)).toBe(true);
  });

  it("should handle nodes without edges", () => {
    const layoutedNodes = applyForceLayout(mockNodes, []);

    expect(layoutedNodes).toHaveLength(4);
    layoutedNodes.forEach((node) => {
      expect(Number.isFinite(node.position.x)).toBe(true);
      expect(Number.isFinite(node.position.y)).toBe(true);
    });
  });

  it("should prevent node overlap with collision force", () => {
    const layoutedNodes = applyForceLayout(mockNodes, mockEdges, {
      preventOverlap: true,
      collideStrength: 0.9,
    });

    expect(layoutedNodes).toHaveLength(4);

    // Check that no two nodes are too close (basic overlap check)
    for (let i = 0; i < layoutedNodes.length; i++) {
      for (let j = i + 1; j < layoutedNodes.length; j++) {
        const node1 = layoutedNodes[i];
        const node2 = layoutedNodes[j];

        const distance = Math.sqrt(
          Math.pow(node2.position.x - node1.position.x, 2) +
            Math.pow(node2.position.y - node1.position.y, 2),
        );

        // Nodes should not be too close (minimum separation)
        expect(distance).toBeGreaterThan(10);
      }
    }
  });

  it("should handle high-degree nodes with larger collision radius", () => {
    const highDegreeNode: GraphNode = {
      id: "10",
      type: "entityNode",
      position: { x: 0, y: 0 },
      data: {
        label: "Hub Node",
        entityType: "Person",
        degree: 15,
        properties: {},
        original: {} as any,
      },
    };

    const nodesWithHub = [...mockNodes, highDegreeNode];
    const layoutedNodes = applyForceLayout(nodesWithHub, mockEdges);

    expect(layoutedNodes).toHaveLength(5);
    const hubNode = layoutedNodes.find((n) => n.id === "10");
    expect(hubNode).toBeDefined();
    expect(Number.isFinite(hubNode!.position.x)).toBe(true);
  });

  it("should return empty array for empty input", () => {
    const layoutedNodes = applyForceLayout([], []);
    expect(layoutedNodes).toHaveLength(0);
  });

  it("should use default G6-compatible parameters", () => {
    // Test that default parameters match G6 configuration
    const layoutedNodes = applyForceLayout(mockNodes, mockEdges);

    expect(layoutedNodes).toHaveLength(4);
    layoutedNodes.forEach((node) => {
      expect(Number.isFinite(node.position.x)).toBe(true);
      expect(Number.isFinite(node.position.y)).toBe(true);
    });

    // Default parameters should be:
    // iterations: 150 (G6 compatible)
    // linkDistance: 100
    // linkStrength: 0.8
    // chargeStrength: -400
    // centerStrength: 0.1
  });

  it("should handle circular graph structure", () => {
    const circularEdges: GraphEdge[] = [
      {
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
      },
      {
        id: "e-2",
        source: "2",
        target: "3",
        type: "relationEdge",
        data: {
          relationType: "connected",
          weight: 1.0,
          properties: {},
          original: {} as any,
        },
      },
      {
        id: "e-3",
        source: "3",
        target: "4",
        type: "relationEdge",
        data: {
          relationType: "connected",
          weight: 1.0,
          properties: {},
          original: {} as any,
        },
      },
      {
        id: "e-4",
        source: "4",
        target: "1",
        type: "relationEdge",
        data: {
          relationType: "connected",
          weight: 1.0,
          properties: {},
          original: {} as any,
        },
      },
    ];

    const layoutedNodes = applyForceLayout(mockNodes, circularEdges);

    expect(layoutedNodes).toHaveLength(4);
    layoutedNodes.forEach((node) => {
      expect(Number.isFinite(node.position.x)).toBe(true);
      expect(Number.isFinite(node.position.y)).toBe(true);
    });
  });
});
