/**
 * 关系边组件
 *
 * 映射 G6 的 quadratic 边样式
 *
 * 功能：
 * - 贝塞尔曲线
 * - 箭头
 * - 边标签（关系类型）
 * - 根据 weight 调整样式
 */

import {
  BaseEdge,
  EdgeLabelRenderer,
  type EdgeProps,
  getBezierPath,
} from "@xyflow/react";
import { memo } from "react";
import type { GraphEdge } from "@/types/api/graphs";
import { getEdgeOpacity, getEdgeWidth } from "@/utils/graph/colors";

export const RelationEdge = memo(
  ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    selected,
    markerEnd,
  }: EdgeProps<GraphEdge["data"]>) => {
    const { relationType, weight } = data;

    // 计算贝塞尔曲线路径
    const [edgePath, labelX, labelY] = getBezierPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
    });

    // 根据权重计算样式
    const opacity = getEdgeOpacity(weight);
    const strokeWidth = getEdgeWidth(weight);

    return (
      <>
        {/* 边路径 */}
        <BaseEdge
          id={id}
          path={edgePath}
          markerEnd={markerEnd}
          style={{
            stroke: selected ? "#3b82f6" : "#9ca3af",
            strokeWidth: selected ? strokeWidth + 1 : strokeWidth,
            opacity: selected ? 1 : opacity,
          }}
        />

        {/* 边标签 */}
        <EdgeLabelRenderer>
          <div
            className="absolute text-xs font-medium bg-white px-2 py-1 rounded shadow-sm border border-gray-200 pointer-events-none"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              opacity: selected ? 1 : 0.7,
            }}
          >
            {relationType}
          </div>
        </EdgeLabelRenderer>
      </>
    );
  },
);

RelationEdge.displayName = "RelationEdge";
