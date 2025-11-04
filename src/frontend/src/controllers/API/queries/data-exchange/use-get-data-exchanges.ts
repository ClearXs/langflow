import { UseQueryResult, useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";
import {
  DataExchangeQueryParams,
  DataExchangeRecord,
} from "@/types/data-exchange";

/**
 * Hook to fetch data exchange records for a flow
 */
export const useGetDataExchanges = (
  params: DataExchangeQueryParams,
  options?: { enabled?: boolean; refetchInterval?: number },
): UseQueryResult<DataExchangeRecord[], Error> => {
  const getDataExchangesFn = async (): Promise<DataExchangeRecord[]> => {
    const queryParams = new URLSearchParams({
      flow_id: params.flow_id,
    });

    if (params.source_vertex_id) {
      queryParams.append("source_vertex_id", params.source_vertex_id);
    }
    if (params.target_vertex_id) {
      queryParams.append("target_vertex_id", params.target_vertex_id);
    }
    if (params.exchange_type) {
      queryParams.append("exchange_type", params.exchange_type);
    }
    if (params.limit) {
      queryParams.append("limit", params.limit.toString());
    }

    const response = await api.get<DataExchangeRecord[]>(
      `/api/v1/monitor/data-exchanges?${queryParams.toString()}`,
    );
    return response.data;
  };

  return useQuery({
    queryKey: ["data-exchanges", params],
    queryFn: getDataExchangesFn,
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
  });
};
