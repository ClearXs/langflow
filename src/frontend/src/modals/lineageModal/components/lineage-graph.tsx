import {
  Background,
  BaseEdge,
  Controls,
  type Edge,
  EdgeLabelRenderer,
  type EdgeProps,
  getBezierPath,
  getSmoothStepPath,
  Handle,
  MarkerType,
  type Node,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import "@xyflow/react/dist/style.css";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import type { LineageRelationship, LineageTable } from "../use-get-lineage";

interface LineageGraphProps {
  tables: LineageTable[];
  relationships: LineageRelationship[];
}

// Custom node component for tables
const TableNode = ({ data }: { data: any }) => {
  const { t } = useTranslation();
  const isSource = data.type === "source";
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border-2 bg-background p-3 shadow-md ${
        isSource ? "border-blue-500" : "border-green-500"
      }`}
      style={{ minWidth: "240px", maxWidth: "320px" }}
    >
      {/* Input handle for target tables */}
      {!isSource && (
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: "#555" }}
        />
      )}

      <div className="mb-2 flex items-center gap-2">
        <ForwardedIconComponent
          name="Database"
          className={`h-4 w-4 ${isSource ? "text-blue-600" : "text-green-600"}`}
        />
        <div className="font-semibold">{data.table_name}</div>
      </div>

      {data.datasource_name && (
        <div className="mb-1 text-xs text-muted-foreground">
          {data.datasource_name}
        </div>
      )}

      {data.fields && data.fields.length > 0 && (
        <div className="mt-2 border-t pt-2">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium text-foreground">
              {t("lineage.fields")}
            </span>
            <span className="text-muted-foreground">
              ({data.fields.length})
            </span>
          </div>
          <div className="mt-1 max-h-32 space-y-0.5 overflow-auto text-xs">
            {(expanded ? data.fields : data.fields.slice(0, 5)).map(
              (field: any, idx: number) => (
                <div key={idx} className="flex items-center gap-1">
                  {field.is_key && (
                    <ForwardedIconComponent
                      name="Key"
                      className="h-3 w-3 text-yellow-600"
                    />
                  )}
                  <span className="text-foreground">{field.name}</span>
                  <span className="text-muted-foreground">({field.type})</span>
                </div>
              ),
            )}
            {data.fields.length > 5 && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                {expanded
                  ? t("lineage.showLess")
                  : t("lineage.showMore", {
                      count: data.fields.length - 5,
                    })}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Output handle for source tables */}
      {isSource && (
        <Handle
          type="source"
          position={Position.Right}
          style={{ background: "#555" }}
        />
      )}
    </div>
  );
};

// Custom node component for transformation nodes
const TransformNode = ({ data }: { data: any }) => {
  return (
    <div
      className="rounded-lg border-2 border-orange-500 bg-background p-3 shadow-md"
      style={{ minWidth: "180px", maxWidth: "240px" }}
    >
      {/* Input handle for receiving data from source */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "#555" }}
      />

      <div className="mb-1 flex items-center gap-2">
        <ForwardedIconComponent
          name="Workflow"
          className="h-4 w-4 text-orange-600"
        />
        <div className="text-sm font-semibold">{data.name}</div>
      </div>
      <div className="text-xs text-muted-foreground">{data.type}</div>

      {/* Output handle for sending data to target */}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "#555" }}
      />
    </div>
  );
};

// Simple edge component for data flow connections
const DataFlowEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
}: EdgeProps) => {
  console.log("🔵 DataFlowEdge rendering:", id);

  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  console.log("DataFlowEdge path:", edgePath);

  return (
    <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
  );
};

// Custom edge component with field mapping information
const FieldMappingEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
  style,
}: EdgeProps) => {
  const { t } = useTranslation();
  const [showMappings, setShowMappings] = useState(false);

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const fieldMappings = data?.fieldMappings || [];
  const hasFieldMappings = fieldMappings.length > 0;

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        {hasFieldMappings && (
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
            }}
            className="nodrag nopan"
          >
            <button
              type="button"
              onClick={() => setShowMappings(!showMappings)}
              className="rounded-md bg-primary px-2 py-1 text-xs text-primary-foreground shadow-md hover:bg-primary/90"
            >
              {fieldMappings.length} {t("lineage.fields")}
            </button>

            {showMappings && (
              <div className="mt-2 max-h-64 w-64 overflow-auto rounded-md border bg-background p-3 shadow-lg">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold">
                    {t("lineage.fieldMappings")}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowMappings(false)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <ForwardedIconComponent name="X" className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-2">
                  {fieldMappings.map((mapping: any, idx: number) => (
                    <div
                      key={idx}
                      className="rounded border-l-2 border-blue-500 bg-muted p-2 text-xs"
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-medium text-foreground">
                          {mapping.source_field}
                        </span>
                        <ForwardedIconComponent
                          name="ArrowRight"
                          className="h-3 w-3 text-muted-foreground"
                        />
                        <span className="font-medium text-foreground">
                          {mapping.target_field}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <span>{mapping.source_type}</span>
                        {mapping.source_type !== mapping.target_type && (
                          <>
                            <ForwardedIconComponent
                              name="ArrowRight"
                              className="h-3 w-3"
                            />
                            <span>{mapping.target_type}</span>
                          </>
                        )}
                      </div>
                      {mapping.transformations &&
                        mapping.transformations.length > 0 && (
                          <div className="mt-1 text-orange-600">
                            {mapping.transformations.join(", ")}
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
};

const nodeTypes = {
  table: TableNode,
  transformation: TransformNode,
};

const edgeTypes = {
  dataFlow: DataFlowEdge,
  fieldMapping: FieldMappingEdge,
};

// Internal component that uses React Flow hooks
const LineageGraphInternal = ({ tables, relationships }: LineageGraphProps) => {
  const { t } = useTranslation();
  // Generate nodes from tables and transformation paths
  const initialNodes: Node[] = useMemo(() => {
    const sourceTables = tables.filter((t) => t.type === "source");
    const targetTables = tables.filter((t) => t.type === "target");

    const nodes: Node[] = [];
    const transformNodeMap = new Map<string, any>();

    // Position source tables on the left
    sourceTables.forEach((table, idx) => {
      nodes.push({
        id: table.id,
        type: "table",
        position: { x: 50, y: idx * 250 + 50 },
        data: table,
      });
    });

    // Extract all unique transformation nodes from relationships
    relationships.forEach((rel) => {
      if (rel.transformation_path && rel.transformation_path.length > 0) {
        rel.transformation_path.forEach((transform) => {
          if (!transformNodeMap.has(transform.id)) {
            transformNodeMap.set(transform.id, transform);
          }
        });
      }
    });

    // Position transformation nodes in the middle
    const transformNodes = Array.from(transformNodeMap.values());
    transformNodes.forEach((transform, idx) => {
      nodes.push({
        id: transform.id,
        type: "transformation",
        position: { x: 325, y: idx * 200 + 50 },
        data: transform,
      });
    });

    // Position target tables on the right
    targetTables.forEach((table, idx) => {
      nodes.push({
        id: table.id,
        type: "table",
        position: { x: 600, y: idx * 250 + 50 },
        data: table,
      });
    });

    return nodes;
  }, [tables, relationships]);

  // Generate edges from relationships
  const initialEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    let edgeId = 0;

    relationships.forEach((rel) => {
      if (rel.transformation_path && rel.transformation_path.length > 0) {
        // Create chained edges through transformation nodes
        // source → transform1 → transform2 → ... → target

        // First edge: source → first transformation
        edges.push({
          id: `edge-${edgeId++}`,
          source: rel.source_table_id,
          target: rel.transformation_path[0].id,
          animated: true,
          style: {
            stroke: "#3b82f6",
            strokeWidth: 2,
          },
        });

        // Middle edges: transform → transform
        for (let i = 0; i < rel.transformation_path.length - 1; i++) {
          edges.push({
            id: `edge-${edgeId++}`,
            source: rel.transformation_path[i].id,
            target: rel.transformation_path[i + 1].id,
            animated: true,
            style: {
              stroke: "#f97316",
              strokeWidth: 2,
            },
          });
        }

        // Last edge: last transformation → target (with field mappings)
        edges.push({
          id: `edge-${edgeId++}`,
          source:
            rel.transformation_path[rel.transformation_path.length - 1].id,
          target: rel.target_table_id,
          animated: true,
          style: {
            stroke: "#10b981",
            strokeWidth: 2,
          },
        });
      } else {
        // No transformation path, direct connection with field mappings
        edges.push({
          id: rel.id,
          source: rel.source_table_id,
          target: rel.target_table_id,
          animated: true,
          style: {
            stroke: "#6366f1",
            strokeWidth: 2,
          },
        });
      }
    });

    console.log("🚀 Generated edges:", edges);
    return edges;
  }, [relationships]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isInitialized, setIsInitialized] = useState(false);

  // Update nodes and edges when data changes
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
    setIsInitialized(true);
  }, [initialEdges, setEdges]);

  // Temporary debug: Check if edges are being created
  useEffect(() => {
    console.log("=== LINEAGE DEBUG ===");
    console.log("Relationships:", relationships);

    if (edges.length > 0) {
      console.log("✅ Edges created:", edges.length);
      edges.forEach((edge, idx) => {
        console.log(`Edge ${idx}:`, edge);
      });
    } else {
      console.log("❌ No edges found");
    }

    if (nodes.length > 0) {
      console.log("✅ Nodes created:", nodes.length);
      nodes.forEach((node, idx) => {
        console.log(`Node ${idx}:`, {
          id: node.id,
          type: node.type,
          data: node.data?.name || node.data?.table_name,
        });
      });
    }

    console.log("Edge types registered:", Object.keys(edgeTypes));
    console.log("Node types registered:", Object.keys(nodeTypes));
  }, [edges, nodes]);

  if (tables.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <ForwardedIconComponent
            name="Database"
            className="mx-auto mb-2 h-12 w-12"
          />
          <p>{t("lineage.noTablesInFlow")}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
        <Panel position="top-left" className="text-xs text-muted-foreground">
          <div className="rounded-md bg-background p-2 shadow-sm">
            <div className="mb-1 flex items-center gap-2">
              <div className="h-3 w-3 rounded-sm border-2 border-blue-500" />
              <span>{t("lineage.sourceTables")}</span>
            </div>
            <div className="mb-1 flex items-center gap-2">
              <div className="h-3 w-3 rounded-sm border-2 border-orange-500" />
              <span>{t("lineage.transformations")}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-sm border-2 border-green-500" />
              <span>{t("lineage.targetTables")}</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

// Wrapper component that provides React Flow context isolation
const LineageGraph = (props: LineageGraphProps) => {
  return (
    <ReactFlowProvider>
      <LineageGraphInternal {...props} />
    </ReactFlowProvider>
  );
};

export default LineageGraph;
