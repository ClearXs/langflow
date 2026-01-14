/**
 * Hook: useGetEntitiesQuery
 *
 * 获取实体列表（支持分页、过滤、搜索）
 *
 * 后端端点：GET /api/v1/entities/
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type { PaginatedResponse } from "@/types/api";
import type { EntityRead, GetEntitiesParams } from "@/types/api/graphs";

export function useGetEntitiesQuery(params: GetEntitiesParams) {
  return useQuery({
    queryKey: ["entities", params],

    queryFn: async () => {
      const response = await api.get<PaginatedResponse<EntityRead>>(
        "/api/v1/entities/",
        {
          params: {
            space_id: params.space_id,
            entity_type: params.entity_type,
            search: params.search,
            page: params.page || 1,
            page_size: params.page_size || 50,
          },
        },
      );

      return response.data;
    },

    // 仅在 space_id 存在时启用
    enabled: !!params.space_id,

    // 缓存 30 秒
    staleTime: 30000,

    // 失败后重试 1 次
    retry: 1,

    // 后台自动刷新
    refetchOnWindowFocus: true,
  });
}

/**
 * Hook: useGetEntityByIdQuery
 *
 * 获取单个实体详情
 *
 * 后端端点：GET /api/v1/entities/{entity_id}
 */
export function useGetEntityByIdQuery(entityId: number | null) {
  return useQuery({
    queryKey: ["entity", entityId],

    queryFn: async () => {
      if (!entityId) throw new Error("Entity ID is required");

      const response = await api.get<EntityRead>(
        `/api/v1/entities/${entityId}`,
      );
      return response.data;
    },

    enabled: !!entityId,
    staleTime: 60000, // 1 分钟缓存
  });
}
