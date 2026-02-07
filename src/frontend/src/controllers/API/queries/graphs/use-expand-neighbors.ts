/**
 * Hook: useExpandNeighbors
 *
 * 扩展邻居节点（Mutation）
 *
 * 流程：
 * 1. 获取实体的关系
 * 2. 提取新实体 ID
 * 3. 获取新实体详情
 * 4. 返回新节点和边
 *
 * 后端端点：GET /api/v1/graphs/{space_id}/entity/{entity_id}/relations
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";
import type {
  EntityRead,
  ExpandNeighborsRequest,
  ExpandNeighborsResponse,
  RelationRead,
} from "@/types/api/graphs";

interface ExpandNeighborsResult {
  newEntities: EntityRead[];
  newRelations: RelationRead[];
}

export function useExpandNeighbors() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: ExpandNeighborsRequest,
    ): Promise<ExpandNeighborsResult> => {
      // Step 1: 获取实体的所有关系
      const relationsResponse = await api.get<ExpandNeighborsResponse>(
        `/api/v1/graphs/${request.space_id}/entity/${request.entity_id}/relations`,
        {
          params: {
            direction: request.direction || "both",
          },
        },
      );

      const relations = relationsResponse.data.relations;

      // Step 2: 提取新实体 ID（去重）
      const newEntityIds = new Set<number>();
      relations.forEach((rel) => {
        if (rel.source_entity_id !== request.entity_id) {
          newEntityIds.add(rel.source_entity_id);
        }
        if (rel.target_entity_id !== request.entity_id) {
          newEntityIds.add(rel.target_entity_id);
        }
      });

      // Step 3: 并行获取所有新实体的详情
      const entityPromises = Array.from(newEntityIds).map((id) =>
        api.get<EntityRead>(`/api/v1/graph/entities/${id}`),
      );

      const entityResponses = await Promise.all(entityPromises);
      const newEntities = entityResponses.map((res) => res.data);

      return {
        newEntities,
        newRelations: relations,
      };
    },

    onSuccess: (data, variables) => {
      // 使子图缓存失效，触发重新加载
      queryClient.invalidateQueries({
        queryKey: ["subgraph", variables.space_id],
      });
    },

    onError: (error) => {
      console.error("Failed to expand neighbors:", error);
    },
  });
}
