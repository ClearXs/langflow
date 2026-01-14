/**
 * Unit tests for entity transformation utilities
 */

import { describe, expect, it } from "vitest";
import type { EntityRead, RelationRead } from "@/types/api/graphs";
import {
  calculateDegree,
  filterNodesBySearch,
  transformEntitiesToNodes,
  transformEntityToNode,
} from "../transform-entities";

describe("calculateDegree", () => {
  const relations: RelationRead[] = [
    {
      id: 1,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "related_to",
      weight: 1.0,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      description: null,
    },
    {
      id: 2,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 3,
      relation_type: "connected_to",
      weight: 0.8,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      description: null,
    },
    {
      id: 3,
      space_id: 1,
      source_entity_id: 2,
      target_entity_id: 3,
      relation_type: "linked_to",
      weight: 0.5,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      description: null,
    },
  ];

  it("should calculate degree for entity with outgoing and incoming edges", () => {
    expect(calculateDegree(1, relations)).toBe(2);
  });

  it("should calculate degree for entity with mixed edges", () => {
    expect(calculateDegree(2, relations)).toBe(2);
  });

  it("should calculate degree for entity with one edge", () => {
    expect(calculateDegree(3, relations)).toBe(2);
  });

  it("should return 0 for entity with no edges", () => {
    expect(calculateDegree(999, relations)).toBe(0);
  });

  it("should handle empty relations array", () => {
    expect(calculateDegree(1, [])).toBe(0);
  });
});

describe("transformEntityToNode", () => {
  const mockEntity: EntityRead = {
    id: 1,
    space_id: 1,
    name: "Test Entity",
    entity_type: "Person",
    description: "A test entity",
    aliases: ["alias1", "alias2"],
    properties: { key: "value" },
    created_at: "2024-01-01",
    updated_at: null,
    document_id: null,
    chunk_id: null,
    embedding: null,
  };

  it("should transform entity to node with correct structure", () => {
    const node = transformEntityToNode(mockEntity, 5);

    expect(node.id).toBe("1");
    expect(node.type).toBe("entityNode");
    expect(node.data.label).toBe("Test Entity");
    expect(node.data.entityType).toBe("Person");
    expect(node.data.degree).toBe(5);
    expect(node.data.description).toBe("A test entity");
    expect(node.data.properties).toEqual({ key: "value" });
    expect(node.data.original).toBe(mockEntity);
  });

  it("should use default position if not provided", () => {
    const node = transformEntityToNode(mockEntity);
    expect(node.position).toEqual({ x: 0, y: 0 });
  });

  it("should use provided position", () => {
    const node = transformEntityToNode(mockEntity, 0, { x: 100, y: 200 });
    expect(node.position).toEqual({ x: 100, y: 200 });
  });

  it("should default degree to 0 if not provided", () => {
    const node = transformEntityToNode(mockEntity);
    expect(node.data.degree).toBe(0);
  });
});

describe("transformEntitiesToNodes", () => {
  const mockEntities: EntityRead[] = [
    {
      id: 1,
      space_id: 1,
      name: "Entity 1",
      entity_type: "Person",
      description: null,
      aliases: [],
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      embedding: null,
    },
    {
      id: 2,
      space_id: 1,
      name: "Entity 2",
      entity_type: "Organization",
      description: null,
      aliases: [],
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      embedding: null,
    },
  ];

  const mockRelations: RelationRead[] = [
    {
      id: 1,
      space_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "works_at",
      weight: 1.0,
      properties: {},
      created_at: "2024-01-01",
      updated_at: null,
      document_id: null,
      chunk_id: null,
      description: null,
    },
  ];

  it("should transform multiple entities to nodes", () => {
    const nodes = transformEntitiesToNodes(mockEntities, mockRelations);

    expect(nodes).toHaveLength(2);
    expect(nodes[0].id).toBe("1");
    expect(nodes[1].id).toBe("2");
  });

  it("should calculate degrees correctly for each entity", () => {
    const nodes = transformEntitiesToNodes(mockEntities, mockRelations);

    expect(nodes[0].data.degree).toBe(1);
    expect(nodes[1].data.degree).toBe(1);
  });

  it("should handle empty entities array", () => {
    const nodes = transformEntitiesToNodes([], mockRelations);
    expect(nodes).toHaveLength(0);
  });

  it("should work without relations", () => {
    const nodes = transformEntitiesToNodes(mockEntities);

    expect(nodes).toHaveLength(2);
    expect(nodes[0].data.degree).toBe(0);
    expect(nodes[1].data.degree).toBe(0);
  });
});

describe("filterNodesBySearch", () => {
  const mockNodes = [
    {
      id: "1",
      type: "entityNode" as const,
      position: { x: 0, y: 0 },
      data: {
        label: "John Doe",
        entityType: "Person",
        degree: 5,
        properties: {},
        original: {
          id: 1,
          space_id: 1,
          name: "John Doe",
          entity_type: "Person",
          aliases: ["Johnny", "JD"],
          description: "Software engineer",
          properties: {},
          created_at: "2024-01-01",
          updated_at: null,
          document_id: null,
          chunk_id: null,
          embedding: null,
        },
      },
    },
    {
      id: "2",
      type: "entityNode" as const,
      position: { x: 0, y: 0 },
      data: {
        label: "Jane Smith",
        entityType: "Person",
        degree: 3,
        properties: {},
        original: {
          id: 2,
          space_id: 1,
          name: "Jane Smith",
          entity_type: "Person",
          aliases: [],
          description: "Product manager",
          properties: {},
          created_at: "2024-01-01",
          updated_at: null,
          document_id: null,
          chunk_id: null,
          embedding: null,
        },
      },
    },
  ];

  it("should filter nodes by name", () => {
    const filtered = filterNodesBySearch(mockNodes, "john");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].data.label).toBe("John Doe");
  });

  it("should be case insensitive", () => {
    const filtered = filterNodesBySearch(mockNodes, "JANE");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].data.label).toBe("Jane Smith");
  });

  it("should filter by alias", () => {
    const filtered = filterNodesBySearch(mockNodes, "johnny");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].data.label).toBe("John Doe");
  });

  it("should filter by description", () => {
    const filtered = filterNodesBySearch(mockNodes, "engineer");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].data.label).toBe("John Doe");
  });

  it("should return all nodes for empty query", () => {
    const filtered = filterNodesBySearch(mockNodes, "");
    expect(filtered).toHaveLength(2);
  });

  it("should return empty array for no matches", () => {
    const filtered = filterNodesBySearch(mockNodes, "nonexistent");
    expect(filtered).toHaveLength(0);
  });

  it("should trim whitespace from query", () => {
    const filtered = filterNodesBySearch(mockNodes, "  john  ");
    expect(filtered).toHaveLength(1);
  });
});
