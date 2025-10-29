import { keepPreviousData } from "@tanstack/react-query";
import type { useQueryFunctionType } from "../../../../types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface ExecutionLogsQueryParams {
  flowId: string;
  componentType?: string;
  status?: string;
  vertexId?: string;
  limit?: number;
}

interface ExecutionLogResponse {
  transaction_id: string;
  flow_id: string;
  timestamp: string;
  vertex_id: string;
  target_id?: string;
  inputs: any;
  outputs: any;
  status: string;
  error?: string;
}

interface ExecutionStatsResponse {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  running_executions: number;
  success_rate: number;
  component_types: Record<string, number>;
  performance_metrics: {
    total_duration_ms: number;
    avg_duration_ms: number;
  };
  latest_execution?: string;
  earliest_execution?: string;
}

export const useGetExecutionLogsQuery: useQueryFunctionType<
  ExecutionLogsQueryParams,
  ExecutionLogResponse[]
> = ({ flowId, componentType, status, vertexId, limit }, options) => {
  const { query } = UseRequestProcessor();

  const getExecutionLogsFn = async () => {
    if (!flowId) return [];

    const params = new URLSearchParams();
    if (componentType) params.append("component_type", componentType);
    if (status) params.append("status", status);
    if (vertexId) params.append("vertex_id", vertexId);
    if (limit) params.append("limit", limit.toString());

    const result = await api.get<ExecutionLogResponse[]>(
      `${getURL("FLOWS")}/${flowId}/logs?${params.toString()}`,
    );

    return result.data;
  };

  const queryResult = query(
    [
      "useGetExecutionLogsQuery",
      flowId,
      { componentType, status, vertexId, limit },
    ],
    getExecutionLogsFn,
    {
      placeholderData: keepPreviousData,
      refetchOnWindowFocus: false,
      ...options,
    },
  );

  return queryResult;
};

export const useGetExecutionStatsQuery: useQueryFunctionType<
  { flowId: string },
  ExecutionStatsResponse
> = ({ flowId }, options) => {
  const { query } = UseRequestProcessor();

  const getExecutionStatsFn = async () => {
    if (!flowId) {
      return {
        total_executions: 0,
        successful_executions: 0,
        failed_executions: 0,
        running_executions: 0,
        success_rate: 0.0,
        component_types: {},
        performance_metrics: {
          total_duration_ms: 0,
          avg_duration_ms: 0,
        },
      };
    }

    const result = await api.get<ExecutionStatsResponse>(
      `${getURL("FLOWS")}/${flowId}/stats`,
    );

    return result.data;
  };

  const queryResult = query(
    ["useGetExecutionStatsQuery", flowId],
    getExecutionStatsFn,
    {
      placeholderData: keepPreviousData,
      refetchOnWindowFocus: false,
      ...options,
    },
  );

  return queryResult;
};

export const useGetTransactionDetailQuery: useQueryFunctionType<
  { flowId: string; transactionId: string },
  ExecutionLogResponse
> = ({ flowId, transactionId }, options) => {
  const { query } = UseRequestProcessor();

  const getTransactionDetailFn = async () => {
    if (!flowId || !transactionId) {
      throw new Error("Flow ID and Transaction ID are required");
    }

    const result = await api.get<ExecutionLogResponse>(
      `${getURL("FLOWS")}/${flowId}/logs/${transactionId}`,
    );

    return result.data;
  };

  const queryResult = query(
    ["useGetTransactionDetailQuery", flowId, transactionId],
    getTransactionDetailFn,
    {
      enabled: !!(flowId && transactionId),
      ...options,
    },
  );

  return queryResult;
};
