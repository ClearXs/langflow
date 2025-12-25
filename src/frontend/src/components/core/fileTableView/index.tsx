import {
  ChevronRight,
  Download,
  Eye,
  Grid3x3,
  List,
  Trash2,
  Upload,
} from "lucide-react";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useFileManagement } from "@/controllers/DATA_API/useFileManagement";
import { useSystemParams } from "@/controllers/DATA_API/useSystemParams";
import ConfirmationModal from "@/modals/confirmationModal";
import DeleteConfirmationModal from "@/modals/deleteConfirmationModal";
import useAlertStore from "@/stores/alertStore";
import { useUploadProgressStore } from "@/stores/uploadProgressStore";
import { cn } from "@/utils/utils";
import { CustomTable } from "./components/CustomTable";
import { FileIcon } from "./components/FileIcon";
import { NavBar } from "./components/NavBar";
import { UploadProgressDrawer } from "./components/UploadProgressDrawer";
import { useFileSystemAccess } from "./hooks/useFileSystemAccess";
import { useFileTable } from "./hooks/useFileTable";
import { type FolderTree, useFolderUpload } from "./hooks/useFolderUpload";
import { useUploadQueue } from "./hooks/useUploadQueue";
import type { FileItem, FileTableViewProps } from "./types";

export interface FileTableViewHandle {
  refresh: () => Promise<void>;
  startCreateFolder: () => void;
}

export const FileTableView = forwardRef<
  FileTableViewHandle,
  FileTableViewProps
>((props, ref) => {
  const { t } = useTranslation();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  // Use file management hook for API operations
  const fileOps = useFileManagement();

  // Use system params hook for preview server
  const systemParams = useSystemParams();
  const [previewServer, setPreviewServer] = useState<string>("");

  const {
    showSize = true,
    showUpdateTime = true,
    showUser = true,
    selectable = true,
    enableContextMenu = true,
    defaultViewMode = "list",
    showViewModeSwitch = true,
    showBreadcrumb = true,
    keepSelection = false,
  } = props;

  const [viewMode, setViewMode] = useState<"list" | "grid">(defaultViewMode);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<FileItem | null>(null);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState(
    t("fileTableModal.newFolder"),
  );
  const [isUploading, setIsUploading] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const fileInputRef = useState<HTMLInputElement | null>(null)[0];
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<FileItem[]>([]);

  // Folder upload state
  const [isUploadDrawerOpen, setIsUploadDrawerOpen] = useState(false);
  const [folderTree, setFolderTree] = useState<FolderTree | null>(null);
  const [showCancelUploadDialog, setShowCancelUploadDialog] = useState(false);

  // Folder upload hooks
  const { parseFolderStructure, createFoldersSerially } =
    useFolderUpload(fileOps);
  const uploadQueue = useUploadQueue(5, fileOps);
  const fileSystemAccess = useFileSystemAccess();

  // Global upload progress store
  const {
    setFolders: setGlobalFolders,
    setTasks: setGlobalTasks,
    setActiveUploads,
    setTotalCompleted,
    setTotalFailed,
    setIsRunning,
    setDrawerOpen: setGlobalDrawerOpen,
    setUploadControls,
  } = useUploadProgressStore();

  // Track upload start parent ID for batch refresh
  const uploadStartParentIdRef = useRef<number | string | null>(null);
  const lastRefreshCountRef = useRef(0);
  const lastRefreshTimeRef = useRef(Date.now());

  const {
    fileList,
    setFileList,
    selectedItems,
    currentParentId,
    currentPath,
    pathHistory,
    hoveredRow,
    contextMenuVisible,
    setContextMenuVisible,
    contextMenuPosition,
    contextMenuFile,
    sortConfig,
    columns,
    fetchFiles,
    navigateToFolder: originalNavigateToFolder,
    navigateToRoot: originalNavigateToRoot,
    navigateToPath: originalNavigateToPath,
    formatFileSize,
    isFileSelectable,
    handleRowClick,
    handleRowDblClick: originalHandleRowDblClick,
    handleSelectionChange,
    handleSortChange,
    handleContextMenu,
    handleMouseEnter,
    handleMouseLeave,
    clearSelection,
  } = useFileTable(props);

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    refresh: fetchFiles,
    startCreateFolder: handleCreateFolder,
  }));

  // Initialize and fetch files - FIXED: Remove fetchFiles from dependencies
  useEffect(() => {
    if (!props.files && props.fetchDataApi) {
      fetchFiles();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.files]);

  // Update file list when props change
  useEffect(() => {
    if (props.files) {
      setFileList(props.files);
    }
  }, [props.files, setFileList]);

  // Fetch kkfileview preview server URL on component mount
  useEffect(() => {
    const fetchPreviewServer = async () => {
      try {
        const res = await systemParams.getList(1, 1000, {
          paramKey: "kkfileview_url",
        });
        if (res.code === 200) {
          if (res.data.records.length > 0) {
            setPreviewServer(res.data.records[0].paramValue);
          }
        }
      } catch (error) {
        console.error("Failed to fetch preview server:", error);
      }
    };
    fetchPreviewServer();
  }, [systemParams]);

  // Batch refresh during upload
  useEffect(() => {
    const BATCH_SIZE = 10;
    const MAX_INTERVAL = 5000; // 5 seconds

    const completedCount = uploadQueue.state.totalCompleted;
    const now = Date.now();

    const batchSizeReached =
      completedCount > 0 &&
      completedCount - lastRefreshCountRef.current >= BATCH_SIZE;

    const timeIntervalReached =
      now - lastRefreshTimeRef.current >= MAX_INTERVAL &&
      completedCount > lastRefreshCountRef.current;

    if (batchSizeReached || timeIntervalReached) {
      // Only refresh if user is still in the same folder
      if (currentParentId === uploadStartParentIdRef.current) {
        fetchFiles();
      }
      lastRefreshCountRef.current = completedCount;
      lastRefreshTimeRef.current = now;
    }
  }, [uploadQueue.state.totalCompleted, currentParentId, fetchFiles]);

  // Final refresh when upload completes
  useEffect(() => {
    if (!uploadQueue.state.isRunning && uploadQueue.state.totalCompleted > 0) {
      if (currentParentId === uploadStartParentIdRef.current) {
        fetchFiles();
      }
    }
  }, [
    uploadQueue.state.isRunning,
    uploadQueue.state.totalCompleted,
    currentParentId,
    fetchFiles,
  ]);

  // Sync upload queue state to global store
  // Only sync when there's actual upload activity to avoid overwriting global state with empty data
  useEffect(() => {
    const hasUploadActivity =
      uploadQueue.state.tasks.length > 0 ||
      folderTree !== null ||
      uploadQueue.state.isRunning ||
      uploadQueue.state.totalCompleted > 0 ||
      uploadQueue.state.totalFailed > 0;

    // Only update global store if there's actual upload activity
    if (hasUploadActivity) {
      setGlobalTasks(uploadQueue.state.tasks);
      setActiveUploads(uploadQueue.state.activeUploads);
      setTotalCompleted(uploadQueue.state.totalCompleted);
      setTotalFailed(uploadQueue.state.totalFailed);
      setIsRunning(uploadQueue.state.isRunning);

      // Sync folder tree to global store
      if (folderTree) {
        setGlobalFolders(folderTree.folders);
      }
    }
  }, [
    uploadQueue.state.tasks,
    uploadQueue.state.activeUploads,
    uploadQueue.state.totalCompleted,
    uploadQueue.state.totalFailed,
    uploadQueue.state.isRunning,
    folderTree,
    setGlobalTasks,
    setActiveUploads,
    setTotalCompleted,
    setTotalFailed,
    setIsRunning,
    setGlobalFolders,
  ]);

  // Sync local drawer state with global store
  useEffect(() => {
    setGlobalDrawerOpen(isUploadDrawerOpen);
  }, [isUploadDrawerOpen, setGlobalDrawerOpen]);

  // Set upload control methods in global store (only once on mount)
  useEffect(() => {
    setUploadControls({
      pauseQueue: uploadQueue.pauseQueue,
      startQueue: uploadQueue.startQueue,
      cancelTask: uploadQueue.cancelTask,
      retryTask: uploadQueue.retryTask,
      clearCompleted: uploadQueue.clearCompleted,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - set only once

  // Handle drawer close with confirmation
  const handleCloseDrawer = () => {
    if (uploadQueue.state.isRunning) {
      setShowCancelUploadDialog(true);
    } else {
      setIsUploadDrawerOpen(false);
    }
  };

  // Confirm cancel upload
  const confirmCancelUpload = () => {
    uploadQueue.pauseQueue();
    uploadQueue.reset();
    setIsUploadDrawerOpen(false);
    setShowCancelUploadDialog(false);
    setFolderTree(null);
  };

  // Path segments for breadcrumb
  const pathSegments = useMemo(() => {
    return currentPath.split("/").filter(Boolean);
  }, [currentPath]);

  // Handle download
  const handleDownload = (file: FileItem) => {
    if (file.type === "folder") {
      setErrorData({
        title: t("fileTableModal.cannotDownloadFolder"),
      });
      return;
    }

    // Use file link if available
    if (file.file?.link) {
      window.open(file.file.link, "_blank");
    } else if (file.id) {
      // Generate download URL using API
      const token = localStorage.getItem("token") || "";
      const downloadUrl = fileOps.getFileDownloadUrl(file.id, token);
      window.location.href = downloadUrl;
    } else {
      setErrorData({
        title: t("fileTableModal.downloadFailed"),
      });
    }
  };

  // Handle delete confirmation
  const confirmDelete = (file: FileItem) => {
    setFileToDelete(file);
    setDeleteDialogOpen(true);
  };

  // Handle delete execution
  const handleDelete = async () => {
    if (!fileToDelete) return;

    try {
      const fileId = fileToDelete.id;

      if (fileToDelete.type === "folder") {
        await fileOps.deleteFolders([fileId]);
      } else {
        await fileOps.deleteFiles([fileId]);
      }

      setSuccessData({
        title: t("fileTableModal.deleteSuccess"),
      });

      setDeleteDialogOpen(false);
      setFileToDelete(null);

      // Refresh file list
      if (props.fetchDataApi) {
        await fetchFiles();
      }
    } catch (error: any) {
      console.error("Delete failed:", error);
      setErrorData({
        title: t("fileTableModal.deleteFailed"),
        list: [error?.message || String(error)],
      });
    }
  };

  // Handle preview
  const handlePreview = (file: FileItem) => {
    if (file.type === "folder") return;

    // Open file in new tab for preview
    if (file.file?.link) {
      // If previewServer is configured, use kkfileview for preview
      if (previewServer) {
        const previewUrl =
          previewServer +
          "/onlinePreview?url=" +
          encodeURIComponent(
            btoa(unescape(encodeURIComponent(file.file.link))),
          );
        window.open(previewUrl, "_blank");
      } else {
        // Fallback: directly open the file link
        window.open(file.file.link, "_blank");
      }
    } else {
      setErrorData({
        title: t("fileTableModal.previewNotAvailable"),
      });
    }
  };

  // Handle create folder
  const handleCreateFolder = () => {
    setIsCreatingFolder(true);
    setNewFolderName(t("fileTableModal.newFolder"));
  };

  // Confirm create folder
  const confirmCreateFolder = async () => {
    if (!newFolderName.trim()) {
      setErrorData({
        title: t("fileTableModal.folderNameRequired"),
      });
      return;
    }

    try {
      // Use currentParentId from useFileTable hook (current folder ID)
      await fileOps.createFolder(currentParentId, newFolderName.trim());

      setSuccessData({
        title: t("fileTableModal.folderCreated"),
      });

      setIsCreatingFolder(false);
      setNewFolderName(t("fileTableModal.newFolder"));

      // Refresh file list
      if (props.fetchDataApi) {
        await fetchFiles();
      }
    } catch (error: any) {
      console.error("Create folder failed:", error);
      setErrorData({
        title: t("fileTableModal.createFolderFailed"),
        list: [error?.message || String(error)],
      });
    }
  };

  // Cancel create folder
  const cancelCreateFolder = () => {
    setIsCreatingFolder(false);
    setNewFolderName(t("fileTableModal.newFolder"));
  };

  // Handle upload file
  const handleUpload = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        await uploadFiles(Array.from(files));
      }
    };
    input.click();
  };

  // Upload files
  const uploadFiles = async (files: File[]) => {
    setIsUploading(true);
    try {
      // Use currentParentId from useFileTable hook (current folder ID)
      for (const file of files) {
        await fileOps.uploadFile(currentParentId, file, (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );
          console.log(`Uploading ${file.name}: ${percentCompleted}%`);
        });
      }

      setSuccessData({
        title: t("common.success"),
        description: t("fileTableModal.uploadSuccess", { count: files.length }),
      });

      // Refresh file list
      if (props.fetchDataApi) {
        await fetchFiles();
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setSuccessData({
        title: t("common.error"),
        description:
          error instanceof Error
            ? error.message
            : t("fileTableModal.uploadFailed"),
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  // Handle folder upload - Directly call appropriate method based on browser support
  const handleUploadFolder = () => {
    if (fileSystemAccess.isSupported) {
      // Modern browsers: directly call File System Access API (no browser dialog)
      confirmFolderUploadModern();
    } else {
      // Legacy browsers: use webkitdirectory (browser's native folder picker)
      confirmFolderUploadLegacy();
    }
  };

  // Legacy fallback: Use webkitdirectory (browser's native folder picker)
  const confirmFolderUploadLegacy = async () => {
    const input = document.createElement("input");
    input.type = "file";
    (input as any).webkitdirectory = true; // Enable folder selection
    input.multiple = true;

    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files || files.length === 0) return;

      await processFolderUpload(Array.from(files));
    };

    input.click();
  };

  // Modern API: Use File System Access API (no browser confirmation dialog)
  const confirmFolderUploadModern = async () => {
    try {
      // Call File System Access API
      const files = await fileSystemAccess.selectDirectory();

      // User cancelled
      if (files.length === 0) {
        return;
      }

      // Process upload
      await processFolderUpload(files);
    } catch (error: any) {
      console.error("Folder upload failed:", error);
      setErrorData({
        title: t("fileTableModal.folderUploadFailed"),
        list: [error?.message || String(error)],
      });
    }
  };

  // Common folder upload processing logic
  // Used by both modern API and legacy fallback
  const processFolderUpload = async (files: File[]) => {
    try {
      setIsUploadDrawerOpen(true);
      uploadStartParentIdRef.current = currentParentId;

      // Parse folder structure
      const tree = parseFolderStructure(files);
      setFolderTree(tree);

      // Create folders serially
      const folderIdMap = await createFoldersSerially(
        tree,
        currentParentId,
        (folder) => {
          setFolderTree((prev) =>
            prev
              ? {
                  ...prev,
                  folders: prev.folders.map((f) =>
                    f.path === folder.path ? folder : f,
                  ),
                }
              : null,
          );
        },
      );

      // Assign folder IDs to files
      tree.files.forEach((f) => {
        // 如果文件在子文件夹，使用映射的文件夹ID；如果在根目录，使用当前父文件夹ID
        f.targetFolderId = f.folderPath
          ? folderIdMap.get(f.folderPath)
          : currentParentId;
      });

      // Enqueue files
      const filesToUpload = tree.files.filter((f) => f.targetFolderId);
      uploadQueue.enqueueFiles(filesToUpload);

      // Start uploads
      uploadQueue.startQueue();

      setSuccessData({
        title: t("fileTableModal.uploadingNFiles", {
          count: tree.files.length,
        }),
      });
    } catch (error: any) {
      console.error("Folder upload failed:", error);
      setErrorData({
        title: t("fileTableModal.folderCreationFailed"),
        list: [error?.message || String(error)],
      });
    }
  };

  // Handle batch delete
  const handleBatchDelete = async () => {
    if (selectedItems.length === 0) {
      setSuccessData({
        title: t("common.warning"),
        description: t("fileTableModal.pleaseSelectFilesToDelete"),
      });
      return;
    }

    // Separate files and folders
    const folderIds: (number | string)[] = [];
    const fileIds: (number | string)[] = [];

    selectedItems.forEach((item) => {
      if (item.type === "folder") {
        folderIds.push(item.id);
      } else {
        fileIds.push(item.id);
      }
    });

    try {
      if (folderIds.length > 0) {
        await fileOps.deleteFolders(folderIds);
      }
      if (fileIds.length > 0) {
        await fileOps.deleteFiles(fileIds);
      }

      setSuccessData({
        title: t("common.success"),
        description: t("fileTableModal.deleteSuccess"),
      });

      // Refresh file list
      if (props.fetchDataApi) {
        await fetchFiles();
      }

      // Clear selection
      handleSelectionChange([]);
    } catch (error) {
      console.error("Batch delete failed:", error);
      setSuccessData({
        title: t("common.error"),
        description:
          error instanceof Error
            ? error.message
            : t("fileTableModal.deleteFailed"),
        variant: "destructive",
      });
    }
  };

  // Clear search state
  const clearSearch = () => {
    setSearchQuery("");
    setIsSearching(false);
    setSearchResults([]);
  };

  // Handle search
  const handleSearch = async (query: string) => {
    setSearchQuery(query);

    if (!query.trim()) {
      clearSearch();
      return;
    }

    setIsSearching(true);
    try {
      // Use fileOps.getFileList with name parameter for backend search
      const results = await fileOps.getFileList(currentParentId, query);
      setSearchResults(results);
    } catch (error) {
      console.error("Search failed:", error);
      setSearchResults([]);
      setErrorData({
        title: t("fileTableModal.searchFailed"),
        list: [error instanceof Error ? error.message : String(error)],
      });
    }
  };

  // Wrap navigation functions to clear search when navigating
  const navigateToFolder = (folder: FileItem) => {
    clearSearch();
    originalNavigateToFolder(folder);
  };

  const navigateToRoot = () => {
    clearSearch();
    originalNavigateToRoot();
  };

  const navigateToPath = (index: number, pathSegments: string[]) => {
    clearSearch();
    originalNavigateToPath(index, pathSegments);
  };

  // Wrap double click to clear search when entering folder
  const handleRowDblClick = (row: FileItem) => {
    if (row.type === "folder") {
      clearSearch();
    }
    originalHandleRowDblClick(row);
  };

  // Handle batch download
  const handleBatchDownload = () => {
    if (selectedItems.length === 0) {
      setSuccessData({
        title: t("common.warning"),
        description: t("fileTableModal.pleaseSelectFilesToDownload"),
      });
      return;
    }

    const filesOnly = selectedItems.filter((file) => file.type !== "folder");

    if (filesOnly.length === 0) {
      setSuccessData({
        title: t("common.warning"),
        description: t("fileTableModal.cannotDownloadFolder"),
      });
      return;
    }

    filesOnly.forEach((file, index) => {
      setTimeout(() => {
        try {
          if (file.file?.link) {
            window.open(file.file.link, "_blank");
          } else if (file.id) {
            const token = localStorage.getItem("token") || "";
            const downloadUrl = fileOps.getFileDownloadUrl(file.id, token);
            window.location.href = downloadUrl;
          }
        } catch (error) {
          console.error(`Download file ${file.name} failed`, error);
          setSuccessData({
            title: t("common.error"),
            description: t("fileTableModal.downloadFailed"),
            variant: "destructive",
          });
        }
      }, index * 500); // 500ms delay between downloads
    });

    setSuccessData({
      title: t("common.success"),
      description: t("fileTableModal.downloadStarted", {
        count: filesOnly.length,
      }),
    });
  };

  // Handle drag events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set to false if leaving the main container
    if (e.currentTarget === e.target) {
      setIsDraggingOver(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);

    // Try to get directory entries using DataTransferItemList API
    const items = e.dataTransfer.items;
    if (items && items.length > 0) {
      const entries: any[] = [];

      // Collect all entries
      for (let i = 0; i < items.length; i++) {
        const entry = items[i].webkitGetAsEntry?.();
        if (entry) {
          entries.push(entry);
        }
      }

      // Check if any entry is a directory
      const hasDirectory = entries.some((entry) => entry.isDirectory);

      if (hasDirectory) {
        // Process as folder upload
        const allFiles: File[] = [];

        // Recursively read all files from directories
        const readDirectory = async (
          dirEntry: any,
          path = "",
        ): Promise<void> => {
          const dirReader = dirEntry.createReader();

          return new Promise<void>((resolve, reject) => {
            const readEntries = () => {
              dirReader.readEntries(async (entries: any[]) => {
                if (entries.length === 0) {
                  resolve();
                  return;
                }

                for (const entry of entries) {
                  if (entry.isFile) {
                    await new Promise<void>((fileResolve) => {
                      entry.file((file: File) => {
                        // Create a new File object with the full path
                        const newFile = new File([file], file.name, {
                          type: file.type,
                          lastModified: file.lastModified,
                        });
                        // Store the path as webkitRelativePath
                        Object.defineProperty(newFile, "webkitRelativePath", {
                          value: path + "/" + file.name,
                          writable: false,
                        });
                        allFiles.push(newFile);
                        fileResolve();
                      });
                    });
                  } else if (entry.isDirectory) {
                    await readDirectory(entry, path + "/" + entry.name);
                  }
                }

                // Continue reading (directories may have more entries)
                readEntries();
              }, reject);
            };

            readEntries();
          });
        };

        // Read all directories
        for (const entry of entries) {
          if (entry.isDirectory) {
            await readDirectory(entry, entry.name);
          } else if (entry.isFile) {
            // Also include files at root level
            await new Promise<void>((resolve) => {
              entry.file((file: File) => {
                allFiles.push(file);
                resolve();
              });
            });
          }
        }

        // Process as folder upload
        if (allFiles.length > 0) {
          await processFolderUpload(allFiles);
        }
        return;
      }
    }

    // Fallback: treat as regular file upload
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await uploadFiles(files);
    }
  };

  // Render cell content
  const renderCell = (columnProp: string, row: FileItem) => {
    switch (columnProp) {
      case "name":
        return (
          <div className="flex items-center gap-2 w-full">
            <FileIcon fileName={row.name} fileType={row.type} size={24} />
            <TooltipProvider>
              <Tooltip delayDuration={500}>
                <TooltipTrigger asChild>
                  <span
                    className={cn(
                      "truncate flex-1",
                      row.type === "folder" &&
                        "font-medium text-primary cursor-pointer hover:underline",
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (row.type === "folder") {
                        navigateToFolder(row);
                      } else {
                        handlePreview(row);
                      }
                    }}
                  >
                    {row.name}
                  </span>
                </TooltipTrigger>
                <TooltipContent side="top" align="start">
                  <p className="max-w-md break-all">{row.name}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        );

      case "updateTime":
        return <span>{row.updateTime || "-"}</span>;

      case "size":
        return (
          <span>
            {row.type === "folder"
              ? "-"
              : formatFileSize(row.file?.size || row.size)}
          </span>
        );

      case "createUser":
        return <span>{row.createUser || "-"}</span>;

      case "actions":
        return (
          <div className="flex items-center gap-1">
            {row.type !== "folder" && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePreview(row);
                  }}
                >
                  <Eye className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload(row);
                  }}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={(e) => {
                e.stopPropagation();
                confirmDelete(row);
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        );

      default:
        return <span>{String(row[columnProp as keyof FileItem] || "-")}</span>;
    }
  };

  // Render grid item
  const renderGridItem = (row: FileItem) => {
    return (
      <>
        <FileIcon fileName={row.name} fileType={row.type} size={48} />
        <div className="w-full truncate text-center text-sm font-medium">
          {row.name}
        </div>
        {row.type !== "folder" && (
          <div className="text-xs text-muted-foreground">
            {formatFileSize(row.file?.size || row.size)}
          </div>
        )}
      </>
    );
  };

  // Determine which file list to display (search results or normal file list)
  const displayFileList = isSearching ? searchResults : fileList;

  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Navigation bar with actions */}
      <NavBar
        searchQuery={searchQuery}
        selectedFile={selectedItems[0]}
        selectList={selectedItems}
        onCreate={handleCreateFolder}
        onUpload={handleUpload}
        onUploadFolder={handleUploadFolder}
        onSearch={handleSearch}
        onDownload={handleBatchDownload}
        onBatchDelete={handleBatchDelete}
      />

      {/* Create folder inline input */}
      {isCreatingFolder && (
        <div className="flex items-center gap-2 border-b px-4 py-2 bg-muted/50">
          <FileIcon
            fileName={t("fileTableModal.newFolder")}
            fileType="folder"
            size={24}
          />
          <Input
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                confirmCreateFolder();
              } else if (e.key === "Escape") {
                cancelCreateFolder();
              }
            }}
            className="h-8 w-64"
            autoFocus
          />
          <Button
            size="sm"
            variant="ghost"
            onClick={confirmCreateFolder}
            disabled={!newFolderName.trim()}
          >
            {t("common.confirm")}
          </Button>
          <Button size="sm" variant="ghost" onClick={cancelCreateFolder}>
            {t("common.cancel")}
          </Button>
        </div>
      )}

      {/* Breadcrumb navigation */}
      {showBreadcrumb && (
        <div className="flex items-center justify-between border-b px-4 py-2">
          <div className="flex items-center gap-2 text-sm">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                onClick={navigateToRoot}
              >
                {t("fileTableModal.allFiles")}
              </Button>
              {pathSegments.map((segment, index) => (
                <div key={index} className="flex items-center gap-1">
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2"
                    onClick={() => navigateToPath(index, pathSegments)}
                  >
                    {segment}
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* View mode toggle */}
          {showViewModeSwitch && (
            <div className="flex items-center gap-1">
              <Button
                variant={viewMode === "list" ? "default" : "ghost"}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode("list")}
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "grid" ? "default" : "ghost"}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode("grid")}
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      )}

      {/* File table */}
      <div
        className="flex-1 overflow-hidden relative"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        {isDraggingOver && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-primary/10 border-4 border-dashed border-primary backdrop-blur-sm">
            <div className="text-center">
              <Upload className="h-16 w-16 mx-auto mb-4 text-primary" />
              <p className="text-lg font-semibold text-primary">
                {t("fileTableModal.dropFilesHere")}
              </p>
            </div>
          </div>
        )}

        <CustomTable
          data={displayFileList}
          columns={columns}
          viewMode={viewMode}
          selectable={selectable}
          selectedItems={selectedItems}
          sortConfig={sortConfig}
          isFileSelectable={isFileSelectable}
          onRowClick={handleRowClick}
          onRowDblClick={handleRowDblClick}
          onSelectionChange={handleSelectionChange}
          onSortChange={handleSortChange}
          onContextMenu={handleContextMenu}
          onRowMouseEnter={handleMouseEnter}
          onRowMouseLeave={handleMouseLeave}
          renderCell={renderCell}
          renderGridItem={renderGridItem}
        />
      </div>

      {/* Context menu - placeholder */}
      {/* TODO: Implement context menu if needed */}

      {/* Delete confirmation dialog */}
      <DeleteConfirmationModal
        open={deleteDialogOpen}
        setOpen={setDeleteDialogOpen}
        onConfirm={handleDelete}
        description={
          fileToDelete?.type === "folder"
            ? t("common.folder") + " " + fileToDelete?.name
            : t("common.file") + " " + fileToDelete?.name
        }
      >
        <></>
      </DeleteConfirmationModal>

      {/* Cancel upload confirmation dialog */}
      <ConfirmationModal
        title={t("fileTableModal.cancelUploadTitle")}
        cancelText={t("fileTableModal.continueUpload")}
        confirmationText={t("fileTableModal.cancelUpload")}
        open={showCancelUploadDialog}
        onClose={() => setShowCancelUploadDialog(false)}
        onConfirm={confirmCancelUpload}
      >
        <ConfirmationModal.Content>
          <span className="text-sm">
            {t("fileTableModal.cancelUploadMessage")}
          </span>
        </ConfirmationModal.Content>
      </ConfirmationModal>

      {/* Upload progress drawer */}
      <UploadProgressDrawer
        isOpen={isUploadDrawerOpen}
        onClose={handleCloseDrawer}
        folders={folderTree?.folders || []}
        tasks={uploadQueue.state.tasks}
        activeUploads={uploadQueue.state.activeUploads}
        totalCompleted={uploadQueue.state.totalCompleted}
        totalFailed={uploadQueue.state.totalFailed}
        isRunning={uploadQueue.state.isRunning}
        onPause={uploadQueue.pauseQueue}
        onResume={uploadQueue.startQueue}
        onCancel={uploadQueue.cancelTask}
        onRetry={uploadQueue.retryTask}
        onClearCompleted={uploadQueue.clearCompleted}
      />
    </div>
  );
});

FileTableView.displayName = "FileTableView";

// Re-export types
export type { FileItem, FileTableViewProps } from "./types";
