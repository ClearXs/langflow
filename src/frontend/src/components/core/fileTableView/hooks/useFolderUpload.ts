/**
 * useFolderUpload Hook
 *
 * Provides functionality for folder upload with structure preservation:
 * - Parse folder structure from File[] array
 * - Create folders serially (layer by layer, parent before children)
 * - Map local folder paths to server folder IDs
 */

import { useCallback } from "react";
import type { UseFileManagementReturn } from "@/controllers/DATA_API/useFileManagement";

// ==================== Types ====================

export interface FolderNode {
  path: string; // Relative path: "folder1/subfolder"
  name: string; // Folder name: "subfolder"
  parentPath: string; // Parent path: "folder1" (empty string for root)
  depth: number; // Nesting level (0 = root)
  serverId?: number | string; // Server ID after creation
  status: "pending" | "creating" | "created" | "error";
  error?: string;
}

export interface FileToUpload {
  file: File;
  relativePath: string; // From webkitRelativePath
  folderPath: string; // Parent folder path
  targetFolderId?: number | string; // Set after folder creation
  status: "waiting" | "uploading" | "completed" | "error";
  progress: number; // 0-100
  error?: string;
}

export interface FolderTree {
  folders: FolderNode[]; // Sorted by depth (parents first)
  files: FileToUpload[];
  rootFolderName: string;
}

// ==================== Hook ====================

export interface UseFolderUploadReturn {
  parseFolderStructure: (files: File[]) => FolderTree;
  createFoldersSerially: (
    tree: FolderTree,
    currentParentId: number | string,
    onProgress: (folder: FolderNode) => void,
  ) => Promise<Map<string, number | string>>;
}

export function useFolderUpload(
  fileOps: UseFileManagementReturn,
): UseFolderUploadReturn {
  /**
   * Parse folder structure from File array
   * Extracts all unique folder paths and creates a hierarchical tree
   */
  const parseFolderStructure = useCallback((files: File[]): FolderTree => {
    const folderSet = new Set<string>();
    const filesArray: FileToUpload[] = [];

    // Extract all unique folder paths from webkitRelativePath
    for (const file of files) {
      const relativePath = file.webkitRelativePath || file.name;
      const pathParts = relativePath.split("/");

      // Build folder hierarchy (all parent folders)
      let currentPath = "";
      for (let i = 0; i < pathParts.length - 1; i++) {
        currentPath = currentPath
          ? `${currentPath}/${pathParts[i]}`
          : pathParts[i];
        folderSet.add(currentPath);
      }

      // Store file with parent folder path
      const folderPath = pathParts.slice(0, -1).join("/");
      filesArray.push({
        file,
        relativePath,
        folderPath,
        status: "waiting",
        progress: 0,
      });
    }

    // Convert to FolderNode objects
    const folders: FolderNode[] = Array.from(folderSet)
      .map((path) => {
        const parts = path.split("/");
        return {
          path,
          name: parts[parts.length - 1],
          parentPath: parts.slice(0, -1).join("/"),
          depth: parts.length - 1,
          status: "pending" as const,
        };
      })
      // CRITICAL: Sort by depth (parents before children)
      .sort((a, b) => a.depth - b.depth || a.path.localeCompare(b.path));

    return {
      folders,
      files: filesArray,
      rootFolderName: folders[0]?.name || "upload",
    };
  }, []);

  /**
   * Create folders serially (layer by layer)
   * Ensures parent folders are created before children
   */
  const createFoldersSerially = useCallback(
    async (
      tree: FolderTree,
      currentParentId: number | string,
      onProgress: (folder: FolderNode) => void,
    ): Promise<Map<string, number | string>> => {
      const folderIdMap = new Map<string, number | string>();

      // Process folders layer by layer (already sorted by depth)
      for (const folder of tree.folders) {
        try {
          // Update status to creating
          folder.status = "creating";
          onProgress({ ...folder });

          // Determine parent ID
          let parentId = currentParentId;
          if (folder.parentPath) {
            const parentServerId = folderIdMap.get(folder.parentPath);
            if (!parentServerId) {
              throw new Error(
                `Parent folder not created: ${folder.parentPath}`,
              );
            }
            parentId = parentServerId;
          }

          // Create folder on server
          const response = await fileOps.createFolder(parentId, folder.name);

          // Extract folder ID from response (API returns {success, data: <id>, msg})
          const folderId = response.data;

          if (!folderId) {
            throw new Error(`No folder ID returned for: ${folder.name}`);
          }

          // Store mapping
          folderIdMap.set(folder.path, folderId);
          folder.serverId = folderId;
          folder.status = "created";

          console.log(`[FolderUpload] Folder created successfully:`, {
            name: folder.name,
            path: folder.path,
            status: folder.status,
            folderId,
          });

          onProgress({ ...folder });
        } catch (error: any) {
          // Handle "folder already exists" gracefully
          if (
            error.message?.includes("already exists") ||
            error.message?.includes("存在") ||
            error.message?.includes("exist")
          ) {
            try {
              // Try to get existing folder ID
              const parentId = folder.parentPath
                ? folderIdMap.get(folder.parentPath) || currentParentId
                : currentParentId;

              const existingFiles = await fileOps.getFileList(parentId);
              const existingFolder = existingFiles.find(
                (f: any) => f.type === "folder" && f.name === folder.name,
              );

              if (existingFolder?.id) {
                folderIdMap.set(folder.path, existingFolder.id);
                folder.serverId = existingFolder.id;
                folder.status = "created";
                onProgress({ ...folder });
                continue;
              }
            } catch (fetchError) {
              console.error("Failed to fetch existing folder:", fetchError);
            }
          }

          // Mark as error and stop
          folder.status = "error";
          folder.error = error.message || String(error);
          onProgress({ ...folder });
          throw new Error(
            `Failed to create folder "${folder.name}": ${error.message}`,
          );
        }
      }

      return folderIdMap;
    },
    [fileOps],
  );

  return {
    parseFolderStructure,
    createFoldersSerially,
  };
}
