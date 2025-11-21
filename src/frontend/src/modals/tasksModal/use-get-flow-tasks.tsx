import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";
import type { TasksListResponse } from "./types";

export const useGetFlowTasks = (
  flowId: string,
  isModalOpen: boolean,
  status?: string,
  limit: number = 50,
  offset: number = 0,
) => {
  return useQuery({
    queryKey: ["flow-tasks", flowId, status, limit, offset],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      if (status) {
        params.append("status", status);
      }

      const response = await api.get<TasksListResponse>(
        `/api/v1/tasks/flows/${flowId}/tasks?${params.toString()}`,
      );

      return response.data;
    },
    enabled: !!flowId && isModalOpen,
    refetchInterval: isModalOpen ? 20000 : false, // Only refetch when modal is open
  });
};
