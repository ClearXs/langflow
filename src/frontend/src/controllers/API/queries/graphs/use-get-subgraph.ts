/**
 * Hook: useGetSubgraphQuery
 *
 * 获取子图数据（BFS 遍历）
 *
 * 后端端点：POST /api/v1/graphs/{space_id}/subgraph
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type { SubgraphRequest, SubgraphResponse } from "@/types/api/graphs";

export function useGetSubgraphQuery(
  spaceId: number | null,
  request: SubgraphRequest,
  options?: {
    enabled?: boolean;
    staleTime?: number;
  },
) {
  return useQuery({
    queryKey: ["subgraph", spaceId, request],

    queryFn: async () => {
      if (!spaceId) throw new Error("Space ID is required");
      if (!request.entity_ids.length)
        throw new Error("At least one entity ID is required");

      const response = await api.post<SubgraphResponse>(
        `/api/v1/graphs/${spaceId}/subgraph`,
        {
          entity_ids: request.entity_ids,
          max_depth: request.max_depth || 2,
          max_nodes: request.max_nodes || 100,
        },
      );

      return response.data;
    },

    // 仅在 spaceId 存在且有 entity_ids 时启用
    enabled:
      options?.enabled !== false && !!spaceId && request.entity_ids.length > 0,

    // 缓存 1 分钟
    staleTime: options?.staleTime || 60000,

    // 子图数据较重要，失败后重试 2 次
    retry: 2,

    // 不在后台自动刷新（避免不必要的请求）
    refetchOnWindowFocus: false,
  });
}
