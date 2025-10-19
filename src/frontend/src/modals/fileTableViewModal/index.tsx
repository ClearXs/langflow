import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ForwardedIconComponent } from "@/components/common/genericIconComponent";
import { FileTableView } from "@/components/core/fileTableView";
import { NavBar } from "@/components/core/fileTableView/components/NavBar";
import type { FileItem } from "@/components/core/fileTableView/types";
import useAlertStore from "@/stores/alertStore";
import BaseModal from "../baseModal";

interface FileTableViewModalProps {
  children?: ReactNode;
  open?: boolean;
  setOpen?: (open: boolean) => void;
  handleSubmit?: (files: FileItem[]) => void;
  selectedFiles?: FileItem[];
  disabled?: boolean;
  // FileTableView props
  showSize?: boolean;
  showUpdateTime?: boolean;
  showUser?: boolean;
  selectable?: boolean;
  selectableFileTypes?: string[];
  defaultViewMode?: "list" | "grid";
  showViewModeSwitch?: boolean;
  showBreadcrumb?: boolean;
  parentId?: number;
  customRootId?: number;
  // API functions
  fetchDataApi?: (parentId: number) => Promise<any>;
  dataTransformer?: (data: any) => FileItem[];
  createFolderApi?: (parentId: number, name: string) => Promise<any>;
  renameFolderApi?: (
    id: number,
    name: string,
    parentId: number,
  ) => Promise<any>;
  deleteFolderApi?: (ids: number[]) => Promise<any>;
  deleteFileApi?: (ids: number[]) => Promise<any>;
  // Modal config
  title?: string;
  description?: string;
  submitLabel?: string;
  allowMultiple?: boolean;
  showNavBar?: boolean;
  showFileDetails?: boolean;
}

export default function FileTableViewModal({
  children,
  open: controlledOpen,
  setOpen: controlledSetOpen,
  handleSubmit,
  selectedFiles = [],
  disabled = false,
  // FileTableView props
  showSize = true,
  showUpdateTime = true,
  showUser = false, // Changed to false to hide creator column
  selectable = true,
  selectableFileTypes,
  defaultViewMode = "list",
  showViewModeSwitch = true,
  showBreadcrumb = true,
  parentId = 0,
  customRootId = 0,
  // API functions
  fetchDataApi,
  dataTransformer,
  createFolderApi,
  renameFolderApi,
  deleteFolderApi,
  deleteFileApi,
  // Modal config
  title,
  description,
  submitLabel,
  allowMultiple = true,
  showNavBar = true,
  showFileDetails = true,
}: FileTableViewModalProps): JSX.Element {
  const { t } = useTranslation();
  const [internalOpen, internalSetOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPath, setCurrentPath] = useState("/");
  const [currentParentId, setCurrentParentId] = useState(parentId);
  const [pathHistory, setPathHistory] = useState<
    Array<{ name: string; id: number }>
  >([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<FileItem[]>([]);
  // Removed isDetailsVisible state as we're not showing file details panel

  const setErrorData = useAlertStore((state) => state.setErrorData);
  const queryClient = useQueryClient();
  const fileTableRef = useRef<any>(null);

  // Internal state for selected files - FIXED: Remove state duplication to prevent flickering
  const [internalSelectedFiles, setInternalSelectedFiles] =
    useState<FileItem[]>(selectedFiles);

  // Use controlled or uncontrolled state
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setIsOpen =
    controlledSetOpen !== undefined ? controlledSetOpen : internalSetOpen;

  // Refetch files when modal opens
  useEffect(() => {
    if (isOpen) {
      queryClient.refetchQueries({
        queryKey: ["useGetFilesV2"],
      });
    }
  }, [isOpen, queryClient]);

  // Reset selected files when modal opens
  useEffect(() => {
    if (isOpen) {
      setInternalSelectedFiles(selectedFiles);
    }
  }, [isOpen, selectedFiles]);

  // FIXED: Handle file selection change without duplication
  const handleSelectionChange = (files: FileItem[]) => {
    if (!allowMultiple && files.length > 1) {
      setInternalSelectedFiles([files[files.length - 1]]);
    } else {
      setInternalSelectedFiles(files);
    }
  };

  // Handle navigation
  const handleNavigation = (folderId: number, path: string) => {
    setCurrentParentId(folderId);
    setCurrentPath(path);
  };

  // Handle search
  const handleSearch = async (query: string) => {
    setSearchQuery(query);

    if (!query.trim()) {
      setIsSearching(false);
      setSearchResults([]);
      if (fileTableRef.current) {
        fileTableRef.current.refresh?.();
      }
      return;
    }

    if (fetchDataApi) {
      setIsSearching(true);
      try {
        const response = await fetchDataApi(currentParentId);
        if (response && response.data && response.data.data) {
          const transformer = dataTransformer || defaultDataTransformer;
          const allFiles = transformer(response.data.data);
          // Filter files by search query
          const filtered = allFiles.filter((file: FileItem) =>
            file.name.toLowerCase().includes(query.toLowerCase()),
          );
          setSearchResults(filtered);
        }
      } catch (error) {
        console.error("Search failed:", error);
      }
    }
  };

  // Default data transformer
  const defaultDataTransformer = (data: any): FileItem[] => {
    return data.map((item: any) => ({
      id: item.id,
      name: item.name,
      type: item.type === "folder" ? "folder" : "file",
      size: item.file?.size || 0,
      updateTime: item.updateTime || new Date().toISOString().split("T")[0],
      createUser: item.createUser || "-",
      path: item.path,
      suffix: item.suffix,
      hasChildren: item.hasChildren,
      file: item.file,
      tags: item.tags,
    }));
  };

  // Handle create folder
  const handleCreate = () => {
    if (fileTableRef.current) {
      fileTableRef.current.startCreateFolder?.();
    }
  };

  // Handle upload
  const handleUpload = () => {
    console.log("Upload file");
    // Implement file upload logic
  };

  // Handle upload folder
  const handleUploadFolder = () => {
    console.log("Upload folder");
    // Implement folder upload logic
  };

  // Handle batch delete
  const handleBatchDelete = async () => {
    if (internalSelectedFiles.length === 0) {
      setErrorData({
        title: t("fileTableModal.pleaseSelectFilesToDelete"),
      });
      return;
    }

    try {
      const folderIds = internalSelectedFiles
        .filter((f) => f.type === "folder")
        .map((f) => f.id as number);
      const fileIds = internalSelectedFiles
        .filter((f) => f.type === "file")
        .map((f) => f.id as number);

      if (folderIds.length > 0 && deleteFolderApi) {
        await deleteFolderApi(folderIds);
      }
      if (fileIds.length > 0 && deleteFileApi) {
        await deleteFileApi(fileIds);
      }

      // Refresh list
      if (fileTableRef.current) {
        fileTableRef.current.refresh?.();
      }

      // Clear selection
      setInternalSelectedFiles([]);
    } catch (error) {
      console.error("Delete failed:", error);
      setErrorData({
        title: t("fileTableModal.deleteFailed"),
      });
    }
  };

  // Handle batch download
  const handleBatchDownload = () => {
    if (internalSelectedFiles.length === 0) {
      setErrorData({
        title: t("fileTableModal.pleaseSelectFilesToDownload"),
      });
      return;
    }

    internalSelectedFiles.forEach((file) => {
      if (file.type === "file" && file.file?.link) {
        window.open(file.file.link, "_blank");
      }
    });
  };

  // FIXED: Handle modal submit with proper validation
  const onSubmit = () => {
    if (internalSelectedFiles.length === 0) {
      setErrorData({
        title: t("fileTableModal.pleaseSelectAtLeastOneFile"),
      });
      return;
    }

    // Submit all selected items (including folders)
    if (handleSubmit) {
      handleSubmit(internalSelectedFiles);
    }
    setIsOpen(false);
  };

  // Get display title and submitLabel with defaults
  const displayTitle = title || t("fileTableModal.fileManager");
  const displaySubmitLabel = submitLabel || t("fileTableModal.selectFiles");

  return (
    <BaseModal
      size="large-h-full"
      open={!disabled && isOpen}
      setOpen={setIsOpen}
      onSubmit={onSubmit}
    >
      <BaseModal.Trigger asChild>
        {children ? children : <></>}
      </BaseModal.Trigger>

      <BaseModal.Header description={description || null}>
        <span className="flex items-center gap-2 font-medium">
          <div className="rounded-md bg-muted p-1.5">
            <ForwardedIconComponent name="FolderOpen" className="h-5 w-5" />
          </div>
          {displayTitle}
        </span>
      </BaseModal.Header>

      <BaseModal.Content overflowHidden>
        <div className="flex h-full flex-col overflow-hidden">
          {/* Navigation Bar */}
          {showNavBar && (
            <div className="shrink-0">
              <NavBar
                searchQuery={searchQuery}
                selectedFile={internalSelectedFiles[0] || null}
                selectList={internalSelectedFiles}
                onCreate={handleCreate}
                onUpload={handleUpload}
                onUploadFolder={handleUploadFolder}
                onSearch={handleSearch}
                onDownload={handleBatchDownload}
                onBatchDelete={handleBatchDelete}
              />
            </div>
          )}

          {/* Main Content */}
          <div className="flex flex-1 overflow-hidden">
            {/* File Table - Full Width */}
            <div className="flex-1 overflow-hidden">
              <FileTableView
                ref={fileTableRef}
                files={isSearching ? searchResults : undefined}
                currentPath={currentPath}
                pathHistory={pathHistory}
                defaultViewMode={defaultViewMode}
                showBreadcrumb={showBreadcrumb}
                showSize={showSize}
                showUpdateTime={showUpdateTime}
                showUser={showUser}
                selectable={selectable}
                selectableFileTypes={selectableFileTypes}
                enableContextMenu={true}
                showViewModeSwitch={showViewModeSwitch}
                parentId={currentParentId}
                customRootId={customRootId}
                fetchDataApi={isSearching ? undefined : fetchDataApi}
                dataTransformer={dataTransformer}
                onFileSelect={handleSelectionChange}
                onSelectionChange={handleSelectionChange}
                onNavigation={handleNavigation}
              />
            </div>
          </div>
        </div>
      </BaseModal.Content>

      <BaseModal.Footer
        submit={{
          label: displaySubmitLabel,
          dataTestId: "select-files-modal-button",
        }}
      />
    </BaseModal>
  );
}
