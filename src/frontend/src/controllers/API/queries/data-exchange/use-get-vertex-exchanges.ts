import { UseQueryResult, useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";
import { VertexExchange } from "@/types/data-exchange";

/**
 * Hook to fetch data exchange history for a specific vertex (component)
 */
export const useGetVertexExchanges = (
  flowId: string,
  vertexId: string,
  options?: { enabled?: boolean; limit?: number },
): UseQueryResult<VertexExchange, Error> => {
  const getVertexExchangesFn = async (): Promise<VertexExchange> => {
    const queryParams = new URLSearchParams({
      flow_id: flowId,
    });

    if (options?.limit) {
      queryParams.append("limit", options.limit.toString());
    }

    const response = await api.get<VertexExchange>(
      `/api/v1/monitor/data-exchanges/vertex/${vertexId}?${queryParams.toString()}`,
    );
    return response.data;
  };

  return useQuery({
    queryKey: ["vertex-exchanges", flowId, vertexId, options?.limit],
    queryFn: getVertexExchangesFn,
    enabled: options?.enabled ?? (!!flowId && !!vertexId),
  });
};
