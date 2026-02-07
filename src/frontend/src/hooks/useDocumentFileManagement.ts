/**
 * Document File Management Adapter
 *
 * This adapter wraps the document API to match the FileManagement interface
 * expected by FileTableView component.
 */

import { useCallback } from "react";
import type { FileItem } from "@/components/core/fileTableView/types";
import {
  useDeleteDocument,
  useGetDocumentsQuery,
  usePostUploadDocuments,
} from "@/controllers/API/queries/documents";
import type { DocumentRead } from "@/types/api/documents";

interface UseDocumentFileManagementReturn {
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
 * Transform DocumentRead to FileItem
 */
function transformDocumentToFileItem(doc: DocumentRead): FileItem {
  return {
    id: doc.id,
    name: doc.title,
    type: "file",
    file: {
      name: doc.title,
      originalName: doc.title,
      size: doc.total_tokens,
    },
    suffix: doc.document_type,
    createTime: doc.created_at,
    updateTime: doc.updated_at,
    size: doc.total_tokens,
  };
}

/**
 * Hook for document file management operations
 * Adapts document API to FileManagement interface
 */
export function useDocumentFileManagement(
  spaceId: number,
): UseDocumentFileManagementReturn {
  const { refetch: refetchDocuments } = useGetDocumentsQuery(
    { search_space_id: spaceId },
    { enabled: false },
  );
  const { mutateAsync: uploadDocuments } = usePostUploadDocuments();
  const { mutateAsync: deleteDocument } = useDeleteDocument();

  /**
   * Get file list (documents)
   */
  const getFileList = useCallback(
    async (parentId?: number | string, name?: string): Promise<FileItem[]> => {
      const result = await refetchDocuments();
      const documents = result.data || [];

      // Filter by name if provided
      let filteredDocs = documents;
      if (name) {
        filteredDocs = documents.filter((doc) =>
          doc.title.toLowerCase().includes(name.toLowerCase()),
        );
      }

      return filteredDocs.map(transformDocumentToFileItem);
    },
    [refetchDocuments],
  );

  /**
   * Create folder - not supported for documents
   */
  const createFolder = useCallback(
    async (parentId: number | string, folderName: string): Promise<any> => {
      throw new Error("Folder creation is not supported for documents");
    },
    [],
  );

  /**
   * Rename resource - not supported for documents
   */
  const renameResource = useCallback(
    async (
      id: number | string,
      newName: string,
      parentId: number | string,
    ): Promise<boolean> => {
      throw new Error("Renaming is not supported for documents");
    },
    [],
  );

  /**
   * Delete folders - not supported for documents
   */
  const deleteFolders = useCallback(
    async (ids: (number | string)[]): Promise<boolean> => {
      throw new Error("Folder deletion is not supported for documents");
    },
    [],
  );

  /**
   * Delete files (documents)
   */
  const deleteFiles = useCallback(
    async (ids: (number | string)[]): Promise<boolean> => {
      try {
        // Delete documents one by one
        await Promise.all(ids.map((id) => deleteDocument({ id: Number(id) })));
        return true;
      } catch (error) {
        console.error("Failed to delete documents:", error);
        throw error;
      }
    },
    [deleteDocument],
  );

  /**
   * Upload file (document)
   */
  const uploadFile = useCallback(
    async (
      folderId: number | string,
      file: File,
      onUploadProgress?: (progressEvent: any) => void,
      signal?: AbortSignal,
    ): Promise<any> => {
      try {
        const result = await uploadDocuments({
          files: [file],
          search_space_id: spaceId,
        });
        return result;
      } catch (error) {
        console.error("Failed to upload document:", error);
        throw error;
      }
    },
    [uploadDocuments, spaceId],
  );

  /**
   * Download file by ID - not implemented yet
   */
  const downloadFileById = useCallback(
    async (
      fileId: number | string,
    ): Promise<{ blob: Blob; filename: string }> => {
      throw new Error("Download is not yet implemented for documents");
    },
    [],
  );

  /**
   * Get file download URL - not implemented yet
   */
  const getFileDownloadUrl = useCallback(
    (fileId: number | string, token: string): string => {
      throw new Error("Download URL is not yet implemented for documents");
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
