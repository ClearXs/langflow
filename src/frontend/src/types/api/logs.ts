// Logs API Type Definitions

export enum LogLevel {
  DEBUG = "DEBUG",
  INFO = "INFO",
  WARNING = "WARNING",
  ERROR = "ERROR",
  CRITICAL = "CRITICAL",
}

export enum LogStatus {
  IN_PROGRESS = "IN_PROGRESS",
  SUCCESS = "SUCCESS",
  FAILED = "FAILED",
}

export interface LogRead {
  id: number;
  level: LogLevel;
  status: LogStatus;
  message: string;
  source: string | null;
  log_metadata: Record<string, any> | null;
  created_at: string;
  search_space_id: number;
}

export interface LogCreate {
  level: LogLevel;
  status: LogStatus;
  message: string;
  source?: string | null;
  log_metadata?: Record<string, any> | null;
  search_space_id: number;
}

export interface LogUpdate {
  level?: LogLevel;
  status?: LogStatus;
  message?: string;
  source?: string | null;
  log_metadata?: Record<string, any> | null;
}

export interface GetLogsParams {
  skip?: number;
  limit?: number;
  search_space_id?: number;
  level?: LogLevel;
  status?: LogStatus;
  source?: string;
  start_date?: string;
  end_date?: string;
}

export interface LogSummary {
  total_logs: number;
  time_window_hours: number;
  by_status: Record<string, number>;
  by_level: Record<string, number>;
  by_source: Record<string, number>;
  active_tasks: Array<{
    id: number;
    task_name: string;
    message: string;
    started_at: string;
    source: string | null;
  }>;
  recent_failures: Array<{
    id: number;
    task_name: string;
    message: string;
    failed_at: string;
    source: string | null;
    error_details: string | null;
  }>;
}

export interface DeleteLogResponse {
  message: string;
}
