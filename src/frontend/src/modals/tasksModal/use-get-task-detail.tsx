import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";

interface Transaction {
  id: string;
  vertex_id: string;
  status: string;
  timestamp: string;
  inputs: Record<string, any> | null;
  outputs: Record<string, any> | null;
  error: string | null;
}

interface TaskDetailResponse {
  task: any;
  transactions: Transaction[];
  data_exchanges: any[];
}

export const useGetTaskDetail = (
  taskId: string | null,
  enabled: boolean = true,
) => {
  return useQuery({
    queryKey: ["task-detail", taskId],
    queryFn: async () => {
      if (!taskId) return null;

      const response = await api.get<TaskDetailResponse>(
        `/api/v1/tasks/${taskId}`,
      );

      return response.data;
    },
    enabled: !!taskId && enabled,
    staleTime: 10000, // Cache for 10 seconds
  });
};
