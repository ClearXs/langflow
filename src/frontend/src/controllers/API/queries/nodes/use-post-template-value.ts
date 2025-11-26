import type { UseMutationResult } from "@tanstack/react-query";
import useFlowStore from "@/stores/flowStore";
import type {
  APIClassType,
  ResponseErrorDetailAPI,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostTemplateValue {
  value: any;
  tool_mode?: boolean;
  action?: string;
  field_name?: string;
}

interface IPostTemplateValueParams {
  node: APIClassType;
  nodeId: string;
  parameterId: string;
}

/**
 * Optimize graph_data by removing code from built-in components
 * and removing temporary metadata fields to prevent data bloat
 * This reduces network payload size (~88% reduction) and prevents
 * exponential nesting of _graph_data in database
 */
const optimizeGraphDataForBackend = (graphData: any): any => {
  if (!graphData || !graphData.nodes) {
    return graphData;
  }

  return {
    ...graphData,
    nodes: graphData.nodes.map((n: any) => {
      const nodeData = n.data?.node;

      // Skip if no template or already optimized
      if (!nodeData?.template) {
        return n;
      }

      // Check if this is a built-in component
      // Built-in: official === true OR (official is undefined AND type is not Custom)
      // Custom: official === false OR type includes 'Custom'
      const isBuiltInComponent =
        nodeData.official === true ||
        (nodeData.official !== false &&
          !nodeData.type?.includes("Custom") &&
          nodeData.type !== "CustomComponent");

      // Remove temporary metadata fields from template to prevent nesting
      // These fields (_graph_data, _node_id) are only needed during API request, not for persistence
      const { _graph_data, _node_id, ...cleanTemplate } = nodeData.template;

      // For built-in components, also remove code value to reduce payload
      if (isBuiltInComponent && cleanTemplate.code) {
        return {
          ...n,
          data: {
            ...n.data,
            node: {
              ...nodeData,
              template: {
                ...cleanTemplate,
                code: {
                  ...cleanTemplate.code,
                  value: "", // Clear code value for built-in components
                  _removed: true, // Mark as removed for validation skip
                },
              },
            },
          },
        };
      }

      // For custom components or components without code field, just remove metadata
      return {
        ...n,
        data: {
          ...n.data,
          node: {
            ...nodeData,
            template: cleanTemplate, // Template without _graph_data and _node_id
          },
        },
      };
    }),
  };
};

export const usePostTemplateValue: useMutationFunctionType<
  IPostTemplateValueParams,
  IPostTemplateValue,
  APIClassType,
  ResponseErrorDetailAPI
> = ({ parameterId, nodeId, node }, options?) => {
  const { mutate } = UseRequestProcessor();
  const getNode = useFlowStore((state) => state.getNode);
  const nodes = useFlowStore((state) => state.nodes);
  const edges = useFlowStore((state) => state.edges);

  const postTemplateValueFn = async (
    payload: IPostTemplateValue,
  ): Promise<APIClassType | undefined> => {
    const template = node.template;

    if (!template) return;
    const lastUpdated = new Date().toISOString();

    // Prepare graph_data for preview operations
    let graphData =
      payload.action && nodes.length > 0
        ? {
            nodes: nodes.map((n) => ({
              id: n.id,
              data: n.data,
              type: n.type,
              position: n.position,
            })),
            edges: edges.map((e) => ({
              id: e.id,
              source: e.source,
              target: e.target,
              sourceHandle: e.sourceHandle,
              targetHandle: e.targetHandle,
            })),
          }
        : undefined;

    // Optimize graph_data by removing code from built-in components
    graphData = optimizeGraphDataForBackend(graphData);

    // Check if current node is built-in component
    // Built-in: official === true OR (official is undefined AND type is not Custom)
    // Custom: official === false OR type includes 'Custom'
    const isBuiltInComponent =
      node.official === true ||
      (node.official !== false &&
        !node.type?.includes("Custom") &&
        node.type !== "CustomComponent");

    // Get component type (vertex_type) from multiple sources
    // Priority:
    // 1. React Flow node's data.type (component type stored in flow)
    // 2. node.type from API response
    // 3. template._type
    // 4. template.type
    // 5. node.display_name (fallback, may be localized)
    const reactFlowNode = getNode(nodeId);
    let vertexType =
      reactFlowNode?.data?.type || // Component type from flow data
      node.type ||
      template._type?.value ||
      template.type?.value;

    // If still "Component" (base class) or empty, use display_name as last resort
    if (!vertexType || vertexType === "Component") {
      vertexType = node.display_name;
    }

    const response = await api.post<APIClassType>(
      getURL("CUSTOM_COMPONENT", { update: "update" }),
      {
        code: isBuiltInComponent ? "" : (template.code?.value ?? ""),
        template: template,
        field: payload.field_name || parameterId,
        field_value: payload.value,
        tool_mode: payload.tool_mode,
        action: payload.action,
        graph_data: graphData,
        node_id: payload.action ? nodeId : undefined, // Send nodeId when action is present
        vertex_type: isBuiltInComponent ? vertexType : undefined, // Send component type for built-in components
      },
    );
    const newTemplate = response.data;
    newTemplate.last_updated = lastUpdated;
    const newNode = getNode(nodeId)?.data?.node as APIClassType | undefined;

    if (
      !newNode?.last_updated ||
      !newTemplate.last_updated ||
      Date.parse(newNode.last_updated) < Date.parse(newTemplate.last_updated)
    ) {
      return newTemplate;
    }

    return undefined;
  };

  const mutation: UseMutationResult<
    APIClassType,
    ResponseErrorDetailAPI,
    IPostTemplateValue
  > = mutate(
    ["usePostTemplateValue", { parameterId, nodeId }],
    postTemplateValueFn,
    {
      ...options,
      retry: 0,
    },
  );

  return mutation;
};
