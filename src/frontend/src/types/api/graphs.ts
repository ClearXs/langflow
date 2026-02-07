/**
 * Graph API Types
 *
 * 对应后端模型：
 * - Entity: src/backend/base/langflow/services/database/models/entity/model.py
 * - Relation: src/backend/base/langflow/services/database/models/relation/model.py
 */

import type { Edge, Node } from "@xyflow/react";

// ==================== 基础实体类型 ====================

/**
 * 实体读取类型
 * 对应后端：EntityRead schema
 */
export interface EntityRead {
  id: number;
  space_id: number;
  document_id: number | null;
  chunk_id: number | null;
  name: string;
  entity_type: string;
  description: string | null;
  aliases: string[];
  embedding: number[] | null;
  properties: Record<string, any>;
  created_at: string; // ISO datetime
  updated_at: string | null;
}

/**
 * 实体创建类型
 * 对应后端：EntityCreate schema
 */
export interface EntityCreate {
  space_id: number;
  document_id?: number | null;
  chunk_id?: number | null;
  name: string;
  entity_type: string;
  description?: string | null;
  aliases?: string[];
  embedding?: number[] | null;
  properties?: Record<string, any>;
}

/**
 * 实体更新类型
 * 对应后端：EntityUpdate schema
 */
export interface EntityUpdate {
  name?: string;
  entity_type?: string;
  description?: string | null;
  aliases?: string[];
  embedding?: number[] | null;
  properties?: Record<string, any>;
}

// ==================== 关系类型 ====================

/**
 * 关系读取类型
 * 对应后端：RelationRead schema
 */
export interface RelationRead {
  id: number;
  space_id: number;
  source_entity_id: number;
  target_entity_id: number;
  document_id: number | null;
  chunk_id: number | null;
  relation_type: string;
  description: string | null;
  weight: number; // 0.0 - 1.0
  properties: Record<string, any>;
  created_at: string;
  updated_at: string | null;
}

/**
 * 关系创建类型
 */
export interface RelationCreate {
  space_id: number;
  source_entity_id: number;
  target_entity_id: number;
  document_id?: number | null;
  chunk_id?: number | null;
  relation_type: string;
  description?: string | null;
  weight?: number;
  properties?: Record<string, any>;
}

// ==================== 图谱查询类型 ====================

/**
 * 子图请求类型
 * 对应后端：SubgraphRequest
 */
export interface SubgraphRequest {
  entity_ids: number[]; // 起始实体 ID 列表（必需）
  max_depth?: number; // 默认 2
  max_nodes?: number; // 默认 100
}

/**
 * 子图响应类型
 * 对应后端：SubgraphResponse
 */
export interface GraphApiNode {
  id: string;
  name: string | null;
  entity_type: string | null;
  description: string | null;
  aliases: string[];
  properties: Record<string, any>;
  space_id: number | null;
  document_id: number | null;
  chunk_id: number | null;
  document_title?: string | null; // Title of the source document
}

export interface GraphApiEdge {
  id: string;
  source: string;
  target: string;
  relation_type: string;
  description: string | null;
  weight: number;
  properties: Record<string, any>;
}

export interface SubgraphResponse {
  nodes: GraphApiNode[];
  edges: GraphApiEdge[];
  raw_paths: any[];
}

/**
 * 获取实体列表请求参数
 */
export interface GetEntitiesParams {
  space_id: number;
  entity_type?: string; // 过滤实体类型
  search?: string; // 搜索名称（部分匹配）
  page?: number; // 默认 1
  page_size?: number; // 默认 50
}

/**
 * 扩展邻居请求
 */
export interface ExpandNeighborsRequest {
  space_id: number;
  entity_id: number;
  direction?: "outgoing" | "incoming" | "both"; // 默认 'both'
}

/**
 * 扩展邻居响应
 */
export interface ExpandNeighborsResponse {
  entity_id: number;
  relations: RelationRead[];
}

/**
 * 图谱统计响应
 * 对应后端：GET /graphs/{space_id}/stats
 */
export interface GraphStatsResponse {
  space_id: number;
  entity_count: number;
  relation_count: number;
  entity_type_distribution: Record<string, number>;
  relation_type_distribution: Record<string, number>;
}

// ==================== ReactFlow 类型 ====================

/**
 * 图谱节点类型（ReactFlow Node + 自定义数据）
 */
export interface GraphNode extends Node {
  type: "entityNode";
  data: {
    label: string;
    entityType: string;
    description?: string | null;
    degree: number; // 节点度数
    properties: Record<string, any>;
    original: EntityRead | GraphApiNode; // 原始实体数据
    documentTitle?: string | null; // Document title for navigation
  };
}

/**
 * 图谱边类型（ReactFlow Edge + 自定义数据）
 */
export interface GraphEdge extends Edge {
  type: "relationEdge";
  label?: string;
  animated?: boolean;
  data: {
    relationType: string;
    weight: number;
    description?: string | null;
    properties: Record<string, any>;
    original: RelationRead; // 原始关系数据
    keywords?: string; // LightRAG semantic keywords
  };
}

// ==================== 布局类型 ====================

/**
 * 布局类型
 */
export type LayoutType = "dagre" | "force";

/**
 * 布局选项
 */
export interface LayoutOptions {
  type: LayoutType;
  direction?: "TB" | "LR" | "BT" | "RL"; // Dagre 方向
  nodeSpacing?: number; // 节点间距
  rankSpacing?: number; // 层级间距
  animate?: boolean; // 动画过渡
}

/**
 * Force 布局配置（映射 G6 Force 配置）
 */
export interface ForceLayoutConfig {
  center?: { x: number; y: number };
  iterations?: number;
  preventOverlap?: boolean;
  nodeSize?: number;
  linkDistance?: number;
  linkStrength?: number;
  chargeStrength?: number;
}

// ==================== 过滤和搜索类型 ====================

/**
 * 图谱过滤器
 */
export interface GraphFilters {
  entityTypes: string[]; // 选中的实体类型
  relationTypes: string[]; // 选中的关系类型
  minWeight?: number; // 最小权重
  maxWeight?: number; // 最大权重
  searchQuery?: string; // 搜索关键词
}

/**
 * 高亮节点选项
 */
export interface HighlightOptions {
  nodeIds: string[]; // 要高亮的节点 ID
  fadedOpacity?: number; // 淡化节点的透明度（默认 0.3）
}
