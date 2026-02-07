/**
 * 实体 → ReactFlow 节点转换
 *
 * 将后端 EntityRead 转换为 ReactFlow Node 格式
 */

import type {
  EntityRead,
  GraphApiNode,
  GraphNode,
  RelationRead,
} from "@/types/api/graphs";

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
  return (entities || []).map((entity) => {
    const degree = calculateDegree(entity.id, relations);
    return transformEntityToNode(entity, degree);
  });
}

export function transformGraphNodesToNodes(
  nodes: GraphApiNode[],
  edges: { source: string; target: string }[] = [],
): GraphNode[] {
  const degreeMap = new Map<string, number>();
  edges.forEach((edge) => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
  });

  return (nodes || []).map((node) => {
    const degree = degreeMap.get(node.id) || 0;

    // Smart label extraction
    // Priority: name > entity_id (from properties) > description (truncated) > id
    let displayLabel = node.name || node.id;
    if (!node.name && node.properties?.entity_id) {
      // LightRAG stores entity name in entity_id field
      displayLabel = node.properties.entity_id;
    } else if (!node.name && !node.properties?.entity_id && node.description) {
      // Fallback to truncated description
      displayLabel =
        node.description.length > 30
          ? node.description.substring(0, 30) + "..."
          : node.description;
    }

    return {
      id: String(node.id),
      type: "entityNode",
      position: { x: 0, y: 0 },
      data: {
        label: displayLabel,
        entityType: node.entity_type || "Other",
        description: node.description,
        degree,
        properties: node.properties || {},
        original: node,
        documentTitle: node.document_title, // Add document title for navigation
      },
    };
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
