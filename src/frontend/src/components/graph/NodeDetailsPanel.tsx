/**
 * 节点详情面板组件
 *
 * 显示选中节点的详细信息，包括：
 * - 实体名称、类型、描述
 * - 关系数量
 * - 来源文档（可点击跳转）
 * - 属性列表
 */

import { ExternalLink, FileText, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { GraphNode } from "@/types/api/graphs";

interface NodeDetailsPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

export function NodeDetailsPanel({ node, onClose }: NodeDetailsPanelProps) {
  const navigate = useNavigate();

  if (!node) return null;

  const { label, entityType, description, degree, properties, documentTitle } =
    node.data;
  const original = node.data.original;

  const handleDocumentClick = () => {
    if ("space_id" in original && "document_id" in original) {
      if (original.space_id && original.document_id) {
        navigate(
          `/spaces/${original.space_id}/documents/${original.document_id}`,
        );
      }
    }
  };

  // 解析 source_chunks（如果存在）
  const sourceChunks =
    properties?.source_chunks || properties?.source_id?.split?.(",") || [];

  return (
    <Card className="absolute top-4 right-4 w-96 max-h-[calc(100vh-8rem)] overflow-y-auto shadow-lg z-10">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-foreground break-words">
              {label}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-primary/10 text-primary rounded">
                {entityType}
              </span>
              <span className="text-sm text-muted-foreground">
                {degree} {degree === 1 ? "connection" : "connections"}
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 ml-2"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <Separator className="my-4" />

        {/* Description */}
        {description && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-foreground mb-2">
              Description
            </h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {description}
            </p>
          </div>
        )}

        {/* Source Document */}
        {documentTitle && "space_id" in original && "document_id" in original && (
          <>
            <Separator className="my-4" />
            <div className="mb-4">
              <h4 className="text-sm font-medium text-foreground mb-2">
                Source Document
              </h4>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDocumentClick}
                className="w-full justify-start text-left"
              >
                <FileText className="h-4 w-4 mr-2 flex-shrink-0" />
                <span className="truncate flex-1">{documentTitle}</span>
                <ExternalLink className="h-3 w-3 ml-2 flex-shrink-0" />
              </Button>
            </div>
          </>
        )}

        {/* Source Chunks */}
        {sourceChunks.length > 0 && (
          <>
            <Separator className="my-4" />
            <div className="mb-4">
              <h4 className="text-sm font-medium text-foreground mb-2">
                Source Chunks ({sourceChunks.length})
              </h4>
              <div className="space-y-1">
                {sourceChunks.slice(0, 5).map((chunk: string, index: number) => (
                  <div
                    key={index}
                    className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded"
                  >
                    {chunk.trim()}
                  </div>
                ))}
                {sourceChunks.length > 5 && (
                  <div className="text-xs text-muted-foreground italic">
                    +{sourceChunks.length - 5} more chunks
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Properties */}
        {Object.keys(properties).length > 0 && (
          <>
            <Separator className="my-4" />
            <div>
              <h4 className="text-sm font-medium text-foreground mb-2">
                Properties
              </h4>
              <div className="space-y-2">
                {Object.entries(properties)
                  .filter(
                    ([key]) =>
                      key !== "source_chunks" &&
                      key !== "source_id" &&
                      key !== "entity_id",
                  )
                  .map(([key, value]) => (
                    <div key={key} className="text-sm">
                      <span className="font-medium text-foreground">{key}:</span>{" "}
                      <span className="text-muted-foreground">
                        {typeof value === "object"
                          ? JSON.stringify(value)
                          : String(value)}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
