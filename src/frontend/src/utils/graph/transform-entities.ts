/**
 * 实体 → ReactFlow 节点转换
 *
 * 将后端 EntityRead 转换为 ReactFlow Node 格式
 */

import type { EntityRead, GraphNode, RelationRead } from "@/types/api/graphs";

/**
 * 计算实体的度数（连接的边数量）
 */
export function calculateDegree(
  entityId: number,
  relations: RelationRead[],
): number {
  return relations.filter(
    (rel) =>
      rel.source_entity_id === entityId || rel.target_entity_id === entityId,
  ).length;
}

/**
 * 转换单个实体为节点
 */
export function transformEntityToNode(
  entity: EntityRead,
  degree: number = 0,
  position?: { x: number; y: number },
): GraphNode {
  return {
    id: String(entity.id),
    type: "entityNode",
    position: position || { x: 0, y: 0 }, // 默认位置，待布局算法计算
    data: {
      label: entity.name,
      entityType: entity.entity_type,
      description: entity.description,
      degree,
      properties: entity.properties,
      original: entity,
    },
  };
}

/**
 * 批量转换实体为节点
 */
export function transformEntitiesToNodes(
  entities: EntityRead[],
  relations: RelationRead[] = [],
): GraphNode[] {
  return entities.map((entity) => {
    const degree = calculateDegree(entity.id, relations);
    return transformEntityToNode(entity, degree);
  });
}

/**
 * 根据搜索关键词过滤节点
 */
export function filterNodesBySearch(
  nodes: GraphNode[],
  searchQuery: string,
): GraphNode[] {
  if (!searchQuery.trim()) return nodes;

  const query = searchQuery.toLowerCase();

  return nodes.filter((node) => {
    // 搜索名称
    if (node.data.label.toLowerCase().includes(query)) return true;

    // 搜索别名
    const aliases = node.data.original.aliases || [];
    if (aliases.some((alias) => alias.toLowerCase().includes(query)))
      return true;

    // 搜索描述
    if (node.data.description?.toLowerCase().includes(query)) return true;

    return false;
  });
}
