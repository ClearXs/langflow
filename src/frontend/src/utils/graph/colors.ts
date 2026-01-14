/**
 * 颜色映射
 *
 * 映射 Yuxi-Know G6 的 colorMap（10 种颜色）
 */

/**
 * 实体类型颜色映射（G6 compatible）
 */
export const ENTITY_TYPE_COLORS: Record<string, string> = {
  // 默认 10 种颜色（映射 G6 colorMap）
  Person: "#5B8FF9", // 蓝色
  Organization: "#5AD8A6", // 绿色
  Location: "#5D7092", // 灰蓝色
  Event: "#F6BD16", // 黄色
  Product: "#E86452", // 红色
  Concept: "#6DC8EC", // 青色
  Technology: "#945FB9", // 紫色
  Document: "#FF9845", // 橙色
  Time: "#1E9493", // 深青色
  Other: "#FF99C3", // 粉色
};

/**
 * 获取实体类型对应的颜色
 */
export function getEntityTypeColor(entityType: string): string {
  return ENTITY_TYPE_COLORS[entityType] || ENTITY_TYPE_COLORS.Other;
}

/**
 * 生成所有唯一实体类型的颜色映射
 */
export function generateColorMap(
  entityTypes: string[],
): Record<string, string> {
  const uniqueTypes = Array.from(new Set(entityTypes));
  const colorMap: Record<string, string> = {};

  const defaultColors = Object.values(ENTITY_TYPE_COLORS);

  uniqueTypes.forEach((type, index) => {
    colorMap[type] = defaultColors[index % defaultColors.length];
  });

  return colorMap;
}

/**
 * 根据权重计算边的透明度
 */
export function getEdgeOpacity(weight: number): number {
  // 权重 0.0-1.0 映射到透明度 0.3-1.0
  return 0.3 + weight * 0.7;
}

/**
 * 根据权重计算边的粗细
 */
export function getEdgeWidth(weight: number): number {
  // 权重 0.0-1.0 映射到宽度 1-4
  return 1 + weight * 3;
}
