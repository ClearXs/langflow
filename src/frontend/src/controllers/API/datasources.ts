import { AxiosError } from "axios";
import { api } from "@/controllers/API/api";
import { dataAPI } from "@/controllers/DATA_API/api";

interface ErrorResponse {
  detail?: string;
  message?: string;
}

export type DataSourceType =
  | "mysql"
  | "postgresql"
  | "hive"
  | "neo4j"
  | "kafka"
  | "flink";

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  status?: "active" | "inactive" | "error";
  lastTested?: string;
  advanced_config?: Record<string, any>; // Advanced configuration as object
  metadata?: {
    created_at: string;
    updated_at?: string;
  };
}

export interface DataSourceCreateInput {
  name: string;
  type: DataSourceType;
  host: string;
  port: number;
  database: string;
  username?: string; // Optional for Hive, Kafka, Flink
  password?: string; // Optional for Hive, Kafka, Flink
  advanced_config?: Record<string, any>; // Optional advanced configuration
}

export interface DataSourceTestInput {
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  type: string;
}

export interface TestConnectionResult {
  status: "success" | "failed";
  message?: string;
}

/**
 * Get all data sources
 */
export async function getDataSources(): Promise<DataSource[]> {
  try {
    const response = await api.get("/api/v1/datasources");
    // Handle both old format (with enterprise/custom) and new format (direct array)
    if (Array.isArray(response.data)) {
      return response.data;
    } else if (response.data.enterprise || response.data.custom) {
      // Legacy format - combine all sources
      return [
        ...(response.data.enterprise || []),
        ...(response.data.custom || []),
      ];
    }
    return [];
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to fetch data sources",
    );
  }
}

/**
 * Get a single data source by ID
 */
export async function getDataSource(id: string): Promise<DataSource> {
  try {
    const response = await api.get(`/api/v1/datasources/${id}`);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to fetch data source",
    );
  }
}

/**
 * Create a new data source
 */
export async function createDataSource(
  data: DataSourceCreateInput,
): Promise<DataSource> {
  try {
    const response = await api.post("/api/v1/datasources", data);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to create data source",
    );
  }
}

/**
 * Update an existing custom data source
 */
export async function updateDataSource(
  id: string,
  data: Partial<DataSourceCreateInput>,
): Promise<DataSource> {
  try {
    const response = await api.put(`/api/v1/datasources/${id}`, data);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to update data source",
    );
  }
}

/**
 * Delete a custom data source
 */
export async function deleteDataSource(id: string): Promise<void> {
  try {
    await api.delete(`/api/v1/datasources/${id}`);
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to delete data source",
    );
  }
}

/**
 * Test a data source connection
 */
export async function testConnection(
  data: DataSourceTestInput,
): Promise<TestConnectionResult> {
  try {
    const response = await api.post("/api/v1/datasources/test", data);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to test connection",
    );
  }
}

/**
 * Test connection for an existing data source
 */
export async function testDataSourceConnection(
  id: string,
): Promise<TestConnectionResult> {
  try {
    const response = await api.post(`/api/v1/datasources/test`, {
      datasource_id: id,
    });
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to test connection",
    );
  }
}

/**
 * Get tables for a data source
 */
export async function getDataSourceTables(id: string): Promise<string[]> {
  try {
    const response = await api.get(`/api/v1/datasources/${id}/tables`);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to fetch tables",
    );
  }
}

/**
 * Get columns for a table in a data source
 */
export async function getTableColumns(
  dataSourceId: string,
  tableName: string,
): Promise<
  Array<{
    name: string;
    type: string;
    nullable: boolean;
    default?: any;
    primary_key?: boolean;
  }>
> {
  try {
    const response = await api.get(
      `/api/v1/datasources/${dataSourceId}/tables/${tableName}/columns`,
    );
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to fetch columns",
    );
  }
}

/**
 * Preview upstream node data for field analysis
 */
export interface PreviewUpstreamRequest {
  input_name: string;
  sample_size?: number;
}

export interface FieldSchema {
  field_name: string;
  data_type: string;
  sample_values?: any[];
}

export interface PreviewUpstreamResponse {
  success: boolean;
  fields: FieldSchema[];
  record_count: number;
  upstream_node_id?: string;
  error?: string;
}

export async function previewUpstreamData(
  flowId: string,
  nodeId: string,
  request: PreviewUpstreamRequest,
): Promise<PreviewUpstreamResponse> {
  try {
    const response = await api.post<PreviewUpstreamResponse>(
      `/api/v1/flows/${flowId}/nodes/${nodeId}/preview_upstream`,
      request,
    );
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    throw new Error(
      axiosError.response?.data?.detail || "Failed to preview upstream data",
    );
  }
}

// ==================== File Management APIs ====================

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

/**
 * Get file list by parent folder ID
 */
export async function getFileList(
  parentId: number = 0,
  name?: string,
): Promise<FileItem[]> {
  try {
    const params: Record<string, any> = { parentId };
    if (name) {
      params.name = name;
    }
    const response = await dataAPI.get<ApiResponse<FileItem[]>>(
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
}

/**
 * Create a new folder
 */
export async function createFolder(
  parentId: number,
  folderName: string,
): Promise<any> {
  try {
    const response = await dataAPI.post<ApiResponse<any>>(
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
}

/**
 * Rename a file or folder
 */
export async function renameResource(
  id: number,
  newName: string,
  parentId: number,
): Promise<boolean> {
  try {
    const response = await dataAPI.post<ApiResponse<boolean>>(
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
}

/**
 * Delete folders
 */
export async function deleteFolders(ids: number[]): Promise<boolean> {
  try {
    const response = await dataAPI.get<ApiResponse<boolean>>(
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
}

/**
 * Delete files
 */
export async function deleteFiles(ids: number[]): Promise<boolean> {
  try {
    const response = await dataAPI.get<ApiResponse<boolean>>(
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
}

/**
 * Upload a file
 */
export async function uploadFile(
  folderId: number,
  file: File,
  onUploadProgress?: (progressEvent: any) => void,
  signal?: AbortSignal,
): Promise<any> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("folderId", folderId.toString());

    const response = await dataAPI.post<ApiResponse<any>>(
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
}

/**
 * Download file URL generator
 */
export function getFileDownloadUrl(fileId: number, token: string): string {
  return `/data-api/data-construction/resource-file/download/${fileId}?Blade-Auth=bearer ${token}`;
}

/**
 * Download file by ID and return as Blob
 */
export async function downloadFileById(fileId: number): Promise<{
  blob: Blob;
  filename: string;
}> {
  try {
    const response = await dataAPI.get(
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
}
