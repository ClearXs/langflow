/**
 * Hook: useGetGraphStatsQuery
 *
 * 获取图谱统计信息
 *
 * 后端端点：GET /api/v1/graphs/{space_id}/stats
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type { GraphStatsResponse } from "@/types/api/graphs";

export function useGetGraphStatsQuery(spaceId: number | null) {
  return useQuery({
    queryKey: ["graph-stats", spaceId],

    queryFn: async () => {
      if (!spaceId) throw new Error("Space ID is required");

      const response = await api.get<GraphStatsResponse>(
        `/api/v1/graphs/${spaceId}/stats`,
      );

      return response.data;
    },

    enabled: !!spaceId,

    // 统计数据不常变，缓存 2 分钟
    staleTime: 120000,

    // 后台自动刷新
    refetchOnWindowFocus: true,
  });
}
