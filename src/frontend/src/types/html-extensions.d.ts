/**
 * TypeScript type extensions for HTML5 File and Directory APIs
 * Adds support for webkitdirectory and webkitRelativePath
 */

declare global {
  interface HTMLInputElement {
    /**
     * Enable folder selection in file input
     * When set to true, the file picker will allow selecting folders instead of files
     * All files within the selected folder (including nested files) will be returned
     */
    webkitdirectory?: boolean;
  }

  interface File {
    /**
     * Relative path of the file within the selected folder
     * Example: "my-folder/subfolder/file.txt"
     * Only available when the file is selected via webkitdirectory
     */
    webkitRelativePath?: string;
  }
}

export {};
