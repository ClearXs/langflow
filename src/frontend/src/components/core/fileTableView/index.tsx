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
import DeleteConfirmationModal from "@/modals/deleteConfirmationModal";
import useAlertStore from "@/stores/alertStore";
import { cn } from "@/utils/utils";
import { CustomTable } from "./components/CustomTable";
import { FileIcon } from "./components/FileIcon";
import { NavBar } from "./components/NavBar";
import { useFileTable } from "./hooks/useFileTable";
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
    navigateToFolder,
    navigateToRoot,
    navigateToPath,
    formatFileSize,
    isFileSelectable,
    handleRowClick,
    handleRowDblClick,
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
      window.open(file.file.link, "_blank");
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

  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Navigation bar with actions */}
      <NavBar
        selectedFile={selectedItems[0]}
        selectList={selectedItems}
        onCreate={handleCreateFolder}
        onUpload={handleUpload}
        onUploadFolder={handleUpload}
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
          data={fileList}
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
    </div>
  );
});

FileTableView.displayName = "FileTableView";

// Re-export types
export type { FileItem, FileTableViewProps } from "./types";
