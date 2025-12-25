/**
 * useFileSystemAccess Hook
 *
 * Provides File System Access API integration for folder upload
 * Automatically falls back to webkitdirectory for unsupported browsers
 */

import { useCallback } from "react";

export interface FileSystemAccessReturn {
  selectDirectory: () => Promise<File[]>;
  isSupported: boolean;
}

export function useFileSystemAccess(): FileSystemAccessReturn {
  const isSupported =
    typeof window !== "undefined" && "showDirectoryPicker" in window;

  /**
   * Recursively read all files from a directory handle
   * Preserves folder structure by adding webkitRelativePath to File objects
   */
  const readDirectoryRecursive = useCallback(
    async (
      dirHandle: FileSystemDirectoryHandle,
      path: string = "",
    ): Promise<File[]> => {
      const files: File[] = [];

      try {
        // Iterate over directory entries
        for await (const entry of dirHandle.values()) {
          const entryPath = path ? `${path}/${entry.name}` : entry.name;

          if (entry.kind === "file") {
            // It's a file - get the File object
            const fileHandle = entry as FileSystemFileHandle;
            const file = await fileHandle.getFile();

            // CRITICAL: Add webkitRelativePath to maintain compatibility
            // with existing parseFolderStructure function
            Object.defineProperty(file, "webkitRelativePath", {
              value: entryPath,
              writable: false,
              enumerable: true,
              configurable: true,
            });

            files.push(file);
          } else if (entry.kind === "directory") {
            // It's a subdirectory - recursively read it
            const subDirHandle = entry as FileSystemDirectoryHandle;
            const subFiles = await readDirectoryRecursive(
              subDirHandle,
              entryPath,
            );
            files.push(...subFiles);
          }
        }
      } catch (error) {
        console.error(`Error reading directory "${path}":`, error);
        throw error;
      }

      return files;
    },
    [],
  );

  /**
   * Show directory picker and return all files
   * Returns empty array if user cancels
   */
  const selectDirectory = useCallback(async (): Promise<File[]> => {
    if (!isSupported) {
      throw new Error(
        "File System Access API is not supported in this browser",
      );
    }

    try {
      // Show directory picker
      const dirHandle = await window.showDirectoryPicker({
        mode: "read", // We only need read access
      });

      // Read all files recursively
      // Use dirHandle.name as root path to preserve folder structure
      const files = await readDirectoryRecursive(dirHandle, dirHandle.name);

      return files;
    } catch (error: any) {
      // User cancelled the picker
      if (error.name === "AbortError") {
        console.log("User cancelled directory selection");
        return [];
      }

      // Permission denied
      if (error.name === "NotAllowedError") {
        throw new Error("Permission to access the directory was denied");
      }

      // Other errors
      console.error("Error selecting directory:", error);
      throw error;
    }
  }, [isSupported, readDirectoryRecursive]);

  return {
    selectDirectory,
    isSupported,
  };
}
