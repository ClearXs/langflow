/**
 * 关系 → ReactFlow 边转换
 *
 * 将后端 RelationRead 转换为 ReactFlow Edge 格式
 */

import type { GraphEdge, RelationRead } from "@/types/api/graphs";

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
  return relations.map(transformRelationToEdge);
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
