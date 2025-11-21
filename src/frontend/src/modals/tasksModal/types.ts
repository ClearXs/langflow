export interface TaskResponse {
  id: string;
  run_id: string;
  flow_id: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  status: "running" | "success" | "error";
  total_components: number;
  success_components: number;
  error_components: number;
  total_data_rows: number;
  total_data_size_mb: number;
  total_exchanges: number;
  total_duration_ms: number | null;
  avg_memory_mb: number;
  user_id: string | null;
  trigger_type: string;
  first_error_component_id: string | null;
  first_error_message: string | null;
  execution_config: Record<string, any> | null;
}

export interface TasksListResponse {
  tasks: TaskResponse[];
  total: number;
  limit: number;
  offset: number;
}
