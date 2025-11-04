import { UseQueryResult, useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";
import { DataExchangeStats } from "@/types/data-exchange";

/**
 * Hook to fetch aggregated data exchange statistics for a flow
 */
export const useGetDataExchangeStats = (
  flowId: string,
  options?: { enabled?: boolean; refetchInterval?: number },
): UseQueryResult<DataExchangeStats, Error> => {
  const getStatsFn = async (): Promise<DataExchangeStats> => {
    const response = await api.get<DataExchangeStats>(
      `/api/v1/monitor/data-exchanges/stats?flow_id=${flowId}`,
    );
    return response.data;
  };

  return useQuery({
    queryKey: ["data-exchange-stats", flowId],
    queryFn: getStatsFn,
    enabled: options?.enabled ?? !!flowId,
    refetchInterval: options?.refetchInterval,
  });
};
