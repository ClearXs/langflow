/**
 * File Management Hooks using DATA_API
 *
 * This module provides React hooks for file and folder management operations
 * using the DATA API with proper authentication.
 */

import { type AxiosError } from "axios";
import { useCallback } from "react";
import { useDataAPI } from "./api";

// ==================== Types ====================

export interface FileItem {
  id: number | string;
  name: string;
  type: "file" | "folder";
  size?: number;
  updateTime?: string;
  createUser?: string;
  path?: string;
  suffix?: string;
  hasChildren?: boolean;
  file?: {
    link?: string;
    domain?: string;
    name?: string;
    originalName?: string;
    size?: number;
    attachId?: number;
  };
  tags?: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  msg?: string;
}

interface ErrorResponse {
  detail?: string;
  message?: string;
}

// ==================== Main Hook ====================

export interface UseFileManagementReturn {
  getFileList: (
    parentId?: number | string,
    name?: string,
  ) => Promise<FileItem[]>;
  createFolder: (parentId: number | string, folderName: string) => Promise<any>;
  renameResource: (
    id: number | string,
    newName: string,
    parentId: number | string,
  ) => Promise<boolean>;
  deleteFolders: (ids: (number | string)[]) => Promise<boolean>;
  deleteFiles: (ids: (number | string)[]) => Promise<boolean>;
  uploadFile: (
    folderId: number | string,
    file: File,
    onUploadProgress?: (progressEvent: any) => void,
    signal?: AbortSignal,
  ) => Promise<any>;
  downloadFileById: (
    fileId: number | string,
  ) => Promise<{ blob: Blob; filename: string }>;
  getFileDownloadUrl: (fileId: number | string, token: string) => string;
}

/**
 * Hook for file and folder management operations
 *
 * @example
 * ```tsx
 * const fileOps = useFileManagement();
 *
 * // Get file list
 * const files = await fileOps.getFileList(0);
 *
 * // Create folder
 * await fileOps.createFolder(0, "New Folder");
 *
 * // Upload file
 * await fileOps.uploadFile(folderId, file, (progress) => {
 *   console.log(progress.loaded / progress.total * 100 + '%');
 * });
 * ```
 */
export function useFileManagement(): UseFileManagementReturn {
  const api = useDataAPI({
    onError: (message) => {
      console.error("[FileManagement]", message);
    },
  });

  /**
   * Get file list by parent folder ID
   */
  const getFileList = useCallback(
    async (
      parentId: number | string = 0,
      name?: string,
    ): Promise<FileItem[]> => {
      try {
        const params: Record<string, any> = { parentId };
        if (name) {
          params.name = name;
        }
        const response = await api.get<ApiResponse<FileItem[]>>(
          "/data-construction/resource-folder/lazy-tree-resources",
          { params },
        );
        return response.data.data || [];
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to fetch file list",
        );
      }
    },
    [api],
  );

  /**
   * Create a new folder
   */
  const createFolder = useCallback(
    async (parentId: number | string, folderName: string): Promise<any> => {
      try {
        const response = await api.post<ApiResponse<any>>(
          "/data-construction/resource-folder/create",
          {
            parentId,
            name: folderName,
          },
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to create folder",
        );
      }
    },
    [api],
  );

  /**
   * Rename a file or folder
   */
  const renameResource = useCallback(
    async (
      id: number | string,
      newName: string,
      parentId: number | string,
    ): Promise<boolean> => {
      try {
        const response = await api.post<ApiResponse<boolean>>(
          "/data-construction/resource-folder/update",
          {
            id,
            name: newName,
            parentId,
          },
        );
        return response.data.data ?? false;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to rename resource",
        );
      }
    },
    [api],
  );

  /**
   * Delete folders
   */
  const deleteFolders = useCallback(
    async (ids: (number | string)[]): Promise<boolean> => {
      try {
        const response = await api.get<ApiResponse<boolean>>(
          "/data-construction/resource-folder/delete",
          {
            params: {
              ids: ids.join(","),
            },
          },
        );
        return response.data.data ?? false;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to delete folders",
        );
      }
    },
    [api],
  );

  /**
   * Delete files
   */
  const deleteFiles = useCallback(
    async (ids: (number | string)[]): Promise<boolean> => {
      try {
        const response = await api.get<ApiResponse<boolean>>(
          "/data-construction/resource-file/delete",
          {
            params: {
              ids: ids.join(","),
            },
          },
        );
        return response.data.data ?? false;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to delete files",
        );
      }
    },
    [api],
  );

  /**
   * Upload a file
   */
  const uploadFile = useCallback(
    async (
      folderId: number | string,
      file: File,
      onUploadProgress?: (progressEvent: any) => void,
      signal?: AbortSignal,
    ): Promise<any> => {
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("folderId", folderId.toString());

        const response = await api.post<ApiResponse<any>>(
          `/data-construction/resource-file/put-file?folderId=${folderId}`,
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
            onUploadProgress,
            signal,
          },
        );
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to upload file",
        );
      }
    },
    [api],
  );

  /**
   * Download file by ID and return as Blob
   */
  const downloadFileById = useCallback(
    async (
      fileId: number | string,
    ): Promise<{ blob: Blob; filename: string }> => {
      try {
        const response = await api.get(
          `/data-construction/resource-file/download/${fileId}`,
          {
            responseType: "blob",
          },
        );

        // Extract filename from Content-Disposition header
        const contentDisposition = response.headers["content-disposition"];
        let filename = `file_${fileId}`;

        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(
            /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/,
          );
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, "");
            // Decode URL-encoded filename
            try {
              filename = decodeURIComponent(filename);
            } catch (e) {
              // Keep original filename if decode fails
            }
          }
        }

        return {
          blob: response.data,
          filename,
        };
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.detail || "Failed to download file",
        );
      }
    },
    [api],
  );

  /**
   * Get file download URL (for direct downloads or previews)
   */
  const getFileDownloadUrl = useCallback(
    (fileId: number | string, token: string): string => {
      return `/data-api/data-construction/resource-file/download/${fileId}?Blade-Auth=bearer ${token}`;
    },
    [],
  );

  return {
    getFileList,
    createFolder,
    renameResource,
    deleteFolders,
    deleteFiles,
    uploadFile,
    downloadFileById,
    getFileDownloadUrl,
  };
}

// Re-export types for convenience
export type { FileItem as FileItemType, ApiResponse as ApiResponseType };
