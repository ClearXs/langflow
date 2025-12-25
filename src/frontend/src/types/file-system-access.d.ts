/**
 * TypeScript type definitions for File System Access API
 * @see https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API
 */

declare global {
  interface Window {
    /**
     * Show a directory picker dialog
     * @throws {AbortError} User cancelled the picker
     * @throws {NotAllowedError} Permission denied
     */
    showDirectoryPicker(
      options?: DirectoryPickerOptions,
    ): Promise<FileSystemDirectoryHandle>;
  }

  interface DirectoryPickerOptions {
    /**
     * Access mode: 'read' or 'readwrite'
     * Default: 'read'
     */
    mode?: "read" | "readwrite";

    /**
     * Suggested starting directory
     */
    startIn?:
      | "desktop"
      | "documents"
      | "downloads"
      | "music"
      | "pictures"
      | "videos";
  }

  /**
   * Base interface for file system handles
   */
  interface FileSystemHandle {
    readonly kind: "file" | "directory";
    readonly name: string;

    /**
     * Check if two handles refer to the same entry
     */
    isSameEntry(other: FileSystemHandle): Promise<boolean>;
  }

  /**
   * File handle - represents a file
   */
  interface FileSystemFileHandle extends FileSystemHandle {
    readonly kind: "file";

    /**
     * Get the File object for this handle
     */
    getFile(): Promise<File>;
  }

  /**
   * Directory handle - represents a directory
   */
  interface FileSystemDirectoryHandle extends FileSystemHandle {
    readonly kind: "directory";

    /**
     * Iterate over entries in this directory
     */
    keys(): AsyncIterableIterator<string>;
    values(): AsyncIterableIterator<FileSystemHandle>;
    entries(): AsyncIterableIterator<[string, FileSystemHandle]>;

    [Symbol.asyncIterator](): AsyncIterableIterator<[string, FileSystemHandle]>;
  }
}

export {};
