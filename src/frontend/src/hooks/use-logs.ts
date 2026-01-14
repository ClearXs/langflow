import { useCallback, useMemo, useState } from "react";
import {
  useDeleteLog,
  useGetLogsQuery,
  useGetLogsSummaryQuery,
} from "@/controllers/API/queries/logs";
import useAlertStore from "@/stores/alertStore";
import type {
  GetLogsParams,
  LogLevel,
  LogRead,
  LogStatus,
  LogSummary,
} from "@/types/api";

export type { LogLevel, LogStatus };

export interface Log extends LogRead {}

export interface LogFilters {
  search_space_id?: number;
  level?: LogLevel;
  status?: LogStatus;
  source?: string;
  start_date?: string;
  end_date?: string;
}

export type { LogSummary };

/**
 * Hook for managing logs with actual API integration
 */
export function useLogs(searchSpaceId?: number, filters: LogFilters = {}) {
  const [error, setError] = useState<string | null>(null);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const memoizedFilters = useMemo(() => filters, [JSON.stringify(filters)]);

  // Build query params for logs API
  const queryParams: GetLogsParams = useMemo(() => {
    const params: GetLogsParams = {
      skip: 0,
      limit: 100,
    };

    if (searchSpaceId) {
      params.search_space_id = searchSpaceId;
    }
    if (memoizedFilters.level) {
      params.level = memoizedFilters.level;
    }
    if (memoizedFilters.status) {
      params.status = memoizedFilters.status;
    }
    if (memoizedFilters.source) {
      params.source = memoizedFilters.source;
    }
    if (memoizedFilters.start_date) {
      params.start_date = memoizedFilters.start_date;
    }
    if (memoizedFilters.end_date) {
      params.end_date = memoizedFilters.end_date;
    }

    return params;
  }, [searchSpaceId, memoizedFilters]);

  // Fetch logs using React Query
  const {
    data: logs = [],
    isLoading: loading,
    refetch,
  } = useGetLogsQuery({ enabled: !!searchSpaceId }, queryParams);

  // Delete log mutation
  const deleteLogMutation = useDeleteLog({
    onError: (error: any) => {
      setErrorData({
        title: "Failed to delete log",
        list: [error?.message || "An error occurred"],
      });
      setError(error?.message || "Failed to delete log");
    },
  });

  // Fetch logs with custom filters
  const fetchLogs = useCallback(
    async (
      customFilters: LogFilters = {},
      options: { skip?: number; limit?: number } = {},
    ) => {
      try {
        setError(null);
        const result = await refetch();
        return result.data || [];
      } catch (err: any) {
        const errorMsg = err?.message || "Failed to fetch logs";
        setError(errorMsg);
        setErrorData({
          title: "Failed to fetch logs",
          list: [errorMsg],
        });
        return [];
      }
    },
    [refetch, setErrorData],
  );

  // Delete multiple logs
  const deleteLogs = useCallback(
    async (logIds: number[]) => {
      try {
        setError(null);
        let deletedCount = 0;

        for (const logId of logIds) {
          await deleteLogMutation.mutateAsync({ logId });
          deletedCount++;
        }

        return { deleted_count: deletedCount };
      } catch (err: any) {
        const errorMsg = err?.message || "Failed to delete logs";
        setError(errorMsg);
        setErrorData({
          title: "Failed to delete logs",
          list: [errorMsg],
        });
        return { deleted_count: 0 };
      }
    },
    [deleteLogMutation, setErrorData],
  );

  // Fetch log summary using React Query
  const fetchLogSummary = useCallback(
    async (
      customFilters: LogFilters = {},
      timeWindowHours: number = 24,
    ): Promise<LogSummary | null> => {
      if (!searchSpaceId) {
        setError("Search space ID is required for log summary");
        return null;
      }

      try {
        setError(null);
        const { data } = await useGetLogsSummaryQuery(
          {},
          { searchSpaceId, hours: timeWindowHours },
        );
        return data || null;
      } catch (err: any) {
        const errorMsg = err?.message || "Failed to fetch log summary";
        setError(errorMsg);
        setErrorData({
          title: "Failed to fetch log summary",
          list: [errorMsg],
        });
        return null;
      }
    },
    [searchSpaceId, setErrorData],
  );

  return {
    logs,
    loading,
    error,
    fetchLogs,
    deleteLogs,
    fetchLogSummary,
    refetch: fetchLogs,
  };
}
