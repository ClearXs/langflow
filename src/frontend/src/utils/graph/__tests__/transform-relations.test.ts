/**
 * Unit tests for relation transformation utilities
 */

import { MarkerType } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import type { RelationRead } from "@/types/api/graphs";
import {
  filterEdgesByType,
  filterEdgesByWeight,
  transformRelationsToEdges,
  transformRelationToEdge,
} from "../transform-relations";

describe("transformRelationToEdge", () => {
  const mockRelation: RelationRead = {
    id: 1,
    space_id: 1,
    source_entity_id: 1,
    target_entity_id: 2,
    relation_type: "works_at",
    weight: 0.9,
    description: "Employment relationship",
    properties: { since: "2020" },
    created_at: "2024-01-01",
    updated_at: null,
    document_id: null,
    chunk_id: null,
  };

  it("should transform relation to edge with correct structure", () => {
    const edge = transformRelationToEdge(mockRelation);

    expect(edge.id).toBe("e-1");
    expect(edge.source).toBe("1");
    expect(edge.target).toBe("2");
    expect(edge.type).toBe("relationEdge");
    expect(edge.label).toBe("works_at");
    expect(edge.data.relationType).toBe("works_at");
    expect(edge.data.weight).toBe(0.9);
    expect(edge.data.description).toBe("Employment relationship");
    expect(edge.data.properties).toEqual({ since: "2020" });
    expect(edge.data.original).toBe(mockRelation);
  });

  it("should set animated true for high weight edges", () => {
    const highWeightRelation = { ...mockRelation, weight: 0.85 };
    const edge = transformRelationToEdge(highWeightRelation);
    expect(edge.animated).toBe(true);
  });

  it("should set animated false for low weight edges", () => {
    const lowWeightRelation = { ...mockRelation, weight: 0.5 };
    const edge = transformRelationToEdge(lowWeightRelation);
    expect(edge.animated).toBe(false);
  });

  it("should include arrow marker", () => {
    const edge = transformRelationToEdge(mockRelation);
    expect(edge.markerEnd).toEqual({ type: MarkerType.ArrowClosed });
  });

  it("should handle relation without description", () => {
    const relationNoDesc = { ...mockRelation, description: null };
    const edge = transformRelationToEdge(relationNoDesc);
    expect(edge.data.description).toBeNull();
  });

  it("should generate unique edge ID from relation ID", () => {
    const relation1 = { ...mockRelation, id: 100 };
    const relation2 = { ...mockRelation, id: 200 };

    const edge1 = transformRelationToEdge(relation1);
    const edge2 = transformRelationToEdge(relation2);

    expect(edge1.id).toBe("e-100");
    expect(edge2.id).toBe("e-200");
    expect(edge1.id).not.toBe(edge2.id);
  });
});

describe("transformRelationsToEdges", () => {
  const mockRelations: RelationRead[] = [
    {
      id: 1,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "works_at",
      weight: 0.9,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 2,
      space_id: 1,
      source_entity_id: 2,
      target_entity_id: 3,
      relation_type: "manages",
      weight: 0.7,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 3,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 3,
      relation_type: "collaborates_with",
      weight: 0.5,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
  ];

  it("should transform multiple relations to edges", () => {
    const edges = transformRelationsToEdges(mockRelations);

    expect(edges).toHaveLength(3);
    expect(edges[0].id).toBe("e-1");
    expect(edges[1].id).toBe("e-2");
    expect(edges[2].id).toBe("e-3");
  });

  it("should preserve relation order", () => {
    const edges = transformRelationsToEdges(mockRelations);

    expect(edges[0].data.relationType).toBe("works_at");
    expect(edges[1].data.relationType).toBe("manages");
    expect(edges[2].data.relationType).toBe("collaborates_with");
  });

  it("should handle empty relations array", () => {
    const edges = transformRelationsToEdges([]);
    expect(edges).toHaveLength(0);
  });

  it("should handle single relation", () => {
    const edges = transformRelationsToEdges([mockRelations[0]]);
    expect(edges).toHaveLength(1);
    expect(edges[0].id).toBe("e-1");
  });
});

describe("filterEdgesByType", () => {
  const mockEdges = transformRelationsToEdges([
    {
      id: 1,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "works_at",
      weight: 0.9,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 2,
      space_id: 1,
      source_entity_id: 2,
      target_entity_id: 3,
      relation_type: "manages",
      weight: 0.7,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 3,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 3,
      relation_type: "works_at",
      weight: 0.8,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
  ]);

  it("should filter edges by single relation type", () => {
    const filtered = filterEdgesByType(mockEdges, ["works_at"]);
    expect(filtered).toHaveLength(2);
    expect(filtered.every((e) => e.data.relationType === "works_at")).toBe(
      true,
    );
  });

  it("should filter edges by multiple relation types", () => {
    const filtered = filterEdgesByType(mockEdges, ["works_at", "manages"]);
    expect(filtered).toHaveLength(3);
  });

  it("should return empty array for no matches", () => {
    const filtered = filterEdgesByType(mockEdges, ["nonexistent"]);
    expect(filtered).toHaveLength(0);
  });

  it("should return all edges for empty types array", () => {
    const filtered = filterEdgesByType(mockEdges, []);
    expect(filtered).toHaveLength(3);
  });
});

describe("filterEdgesByWeight", () => {
  const mockEdges = transformRelationsToEdges([
    {
      id: 1,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "works_at",
      weight: 0.3,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 2,
      space_id: 1,
      source_entity_id: 2,
      target_entity_id: 3,
      relation_type: "manages",
      weight: 0.7,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
    {
      id: 3,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 3,
      relation_type: "collaborates",
      weight: 0.9,
      description: null,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
    },
  ]);

  it("should filter edges by minimum weight", () => {
    const filtered = filterEdgesByWeight(mockEdges, 0.5);
    expect(filtered).toHaveLength(2);
    expect(filtered.every((e) => e.data.weight >= 0.5)).toBe(true);
  });

  it("should filter edges by weight range", () => {
    const filtered = filterEdgesByWeight(mockEdges, 0.5, 0.8);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].data.weight).toBe(0.7);
  });

  it("should return all edges for min 0", () => {
    const filtered = filterEdgesByWeight(mockEdges, 0);
    expect(filtered).toHaveLength(3);
  });

  it("should return empty for very high minimum", () => {
    const filtered = filterEdgesByWeight(mockEdges, 1.0);
    expect(filtered).toHaveLength(0);
  });

  it("should handle inclusive boundaries", () => {
    const filtered = filterEdgesByWeight(mockEdges, 0.7, 0.9);
    expect(filtered).toHaveLength(2);
  });
});
