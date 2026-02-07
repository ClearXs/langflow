/**
 * 关系 → ReactFlow 边转换
 *
 * 将后端 RelationRead 转换为 ReactFlow Edge 格式
 */

import type { GraphApiEdge, GraphEdge, RelationRead } from "@/types/api/graphs";

/**
 * 转换单个关系为边
 */
export function transformRelationToEdge(relation: RelationRead): GraphEdge {
  return {
    id: `e-${relation.id}`,
    source: String(relation.source_entity_id),
    target: String(relation.target_entity_id),
    type: "relationEdge",
    label: relation.relation_type,

    // 高权重关系显示动画
    animated: relation.weight > 0.8,

    data: {
      relationType: relation.relation_type,
      weight: relation.weight,
      description: relation.description,
      properties: relation.properties,
      original: relation,
    },
  };
}

/**
 * 批量转换关系为边
 */
export function transformRelationsToEdges(
  relations: RelationRead[],
): GraphEdge[] {
  return (relations || []).map(transformRelationToEdge);
}

export function transformGraphEdgesToEdges(edges: GraphApiEdge[]): GraphEdge[] {
  return (edges || []).map((edge) => {
    // Smart edge label extraction
    // Priority: first keyword from keywords field > description (truncated) > relation_type > "DIRECTED"
    let edgeLabel = edge.relation_type || "DIRECTED";

    if (edge.properties?.keywords) {
      // Extract first keyword (LightRAG stores as comma-separated string)
      const keywords = edge.properties.keywords.split(",");
      if (keywords.length > 0 && keywords[0].trim()) {
        edgeLabel = keywords[0].trim();
      }
    } else if (edge.description && edge.description.length > 0) {
      // Fallback to truncated description
      edgeLabel =
        edge.description.length > 30
          ? edge.description.substring(0, 30) + "..."
          : edge.description;
    }

    return {
      id: `e-${edge.id}`,
      source: String(edge.source),
      target: String(edge.target),
      type: "relationEdge",
      label: edgeLabel, // Use smart label
      animated: (edge.weight || 0) > 0.8,
      data: {
        relationType: edge.relation_type || "DIRECTED",
        weight: edge.weight || 1.0,
        description: edge.description,
        properties: edge.properties || {},
        original: edge as unknown as RelationRead,
        keywords: edge.properties?.keywords, // Preserve keywords for display
      },
    };
  });
}

/**
 * 根据权重过滤边
 */
export function filterEdgesByWeight(
  edges: GraphEdge[],
  minWeight: number = 0,
  maxWeight: number = 1,
): GraphEdge[] {
  return edges.filter((edge) => {
    const weight = edge.data.weight;
    return weight >= minWeight && weight <= maxWeight;
  });
}

/**
 * 根据关系类型过滤边
 */
export function filterEdgesByType(
  edges: GraphEdge[],
  relationTypes: string[],
): GraphEdge[] {
  if (relationTypes.length === 0) return edges;

  return edges.filter((edge) => relationTypes.includes(edge.data.relationType));
}
