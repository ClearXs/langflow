/**
 * 实体节点组件
 *
 * 映射 G6 的圆形节点样式
 *
 * 功能：
 * - 圆形节点
 * - 根据 degree 动态调整大小
 * - 10 种实体类型颜色
 * - Hover 高亮效果
 * - 拖拽支持
 */

import { Handle, type NodeProps, Position } from "@xyflow/react";
import { memo } from "react";
import { cn } from "@/lib/utils";
import type { GraphNode } from "@/types/api/graphs";
import { getEntityTypeColor } from "@/utils/graph/colors";

export const EntityNode = memo(
  ({ data, selected }: NodeProps<GraphNode["data"]>) => {
    const { label, entityType, degree } = data;

    // 计算节点大小（映射 G6: Math.min(15 + degree * 5, 50)）
    const size = Math.min(60 + degree * 10, 150);

    // 获取实体类型颜色
    const color = getEntityTypeColor(entityType);

    return (
      <div
        className={cn(
          "relative flex items-center justify-center rounded-full transition-all duration-200",
          "border-2 cursor-pointer",
          selected ? "ring-4 ring-blue-500 ring-opacity-50" : "",
        )}
        style={{
          width: size,
          height: size,
          backgroundColor: color,
          borderColor: selected ? "#3b82f6" : "white",
          boxShadow: selected
            ? "0 10px 25px rgba(0, 0, 0, 0.3)"
            : "0 4px 10px rgba(0, 0, 0, 0.2)",
        }}
      >
        {/* 节点 Handles（连接点） */}
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
        />
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
        />

        {/* 节点标签 */}
        <div
          className="absolute text-center font-medium text-white"
          style={{
            fontSize: Math.max(12, size / 8),
            maxWidth: size * 0.8,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>

        {/* Degree 徽章（显示连接数） */}
        {degree > 0 && (
          <div
            className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center"
            style={{
              width: 24,
              height: 24,
            }}
          >
            {degree}
          </div>
        )}
      </div>
    );
  },
);

EntityNode.displayName = "EntityNode";
