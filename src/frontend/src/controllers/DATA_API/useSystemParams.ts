/**
 * System Parameters Management Hooks using DATA_API
 *
 * This module provides React hooks for system parameter management operations
 * using the DATA API with proper authentication.
 */

import { type AxiosError } from "axios";
import { useCallback } from "react";
import { useDataAPI } from "./api";

// ==================== Types ====================

export interface SystemParam {
  id?: string;
  paramName: string;
  paramKey: string;
  paramValue: string;
  remark?: string;
}

// Pagination data type
export interface IPage<T> {
  records: T[];
  total: number;
  size: number;
  current: number;
  pages: number;
}

// Response data type
export interface R<T> {
  code: number;
  success: boolean;
  data: T;
  msg?: string;
}

interface ErrorResponse {
  detail?: string;
  message?: string;
}

// ==================== Main Hook ====================

export interface UseSystemParamsReturn {
  getList: (
    current: number,
    size: number,
    params: Partial<SystemParam>,
  ) => Promise<R<IPage<SystemParam>>>;
  getDetail: (id: string) => Promise<R<SystemParam>>;
  remove: (ids: string[]) => Promise<R<boolean>>;
  add: (row: Partial<SystemParam>) => Promise<R<SystemParam>>;
  update: (row: Partial<SystemParam>) => Promise<R<SystemParam>>;
}

/**
 * Hook for system parameter management operations
 *
 * @example
 * ```tsx
 * const params = useSystemParams();
 *
 * // Get parameter list
 * const res = await params.getList(1, 1000, { paramKey: 'kkfileview_url' });
 * if (res.code === 200 && res.data.records.length > 0) {
 *   const kkfileviewUrl = res.data.records[0].paramValue;
 * }
 *
 * // Get parameter detail
 * const detail = await params.getDetail('param_id');
 *
 * // Add parameter
 * await params.add({
 *   paramName: 'Preview Server',
 *   paramKey: 'kkfileview_url',
 *   paramValue: 'http://localhost:8012',
 * });
 * ```
 */
export function useSystemParams(): UseSystemParamsReturn {
  const api = useDataAPI({
    onError: (message) => {
      console.error("[SystemParams]", message);
    },
  });

  /**
   * Get system parameter list with pagination and filtering
   */
  const getList = useCallback(
    async (
      current: number,
      size: number,
      params: Partial<SystemParam>,
    ): Promise<R<IPage<SystemParam>>> => {
      try {
        const response = await api.get<R<IPage<SystemParam>>>(
          "/blade-system/param/list",
          {
            params: {
              ...params,
              current,
              size,
            },
          },
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to get param list",
        );
      }
    },
    [api],
  );

  /**
   * Get system parameter detail by ID
   */
  const getDetail = useCallback(
    async (id: string): Promise<R<SystemParam>> => {
      try {
        const response = await api.get<R<SystemParam>>(
          "/blade-system/param/detail",
          { params: { id } },
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to get param detail",
        );
      }
    },
    [api],
  );

  /**
   * Remove system parameters by IDs
   */
  const remove = useCallback(
    async (ids: string[]): Promise<R<boolean>> => {
      try {
        const response = await api.post<R<boolean>>(
          "/blade-system/param/remove",
          null,
          { params: { ids } },
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to remove param",
        );
      }
    },
    [api],
  );

  /**
   * Add a new system parameter
   */
  const add = useCallback(
    async (row: Partial<SystemParam>): Promise<R<SystemParam>> => {
      try {
        const response = await api.post<R<SystemParam>>(
          "/blade-system/param/submit",
          row,
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to add param",
        );
      }
    },
    [api],
  );

  /**
   * Update an existing system parameter
   */
  const update = useCallback(
    async (row: Partial<SystemParam>): Promise<R<SystemParam>> => {
      try {
        const response = await api.post<R<SystemParam>>(
          "/blade-system/param/submit",
          row,
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to update param",
        );
      }
    },
    [api],
  );

  return {
    getList,
    getDetail,
    remove,
    add,
    update,
  };
}

// Re-export types for convenience
export type { SystemParam as SystemParamType, R as RType, IPage as IPageType };
