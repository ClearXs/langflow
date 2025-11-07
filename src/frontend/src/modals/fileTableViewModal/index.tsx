import { useQueryClient } from '@tanstack/react-query';
import {
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { ForwardedIconComponent } from '@/components/common/genericIconComponent';
import { FileTableView } from '@/components/core/fileTableView';
import { NavBar } from '@/components/core/fileTableView/components/NavBar';
import type { FileItem } from '@/components/core/fileTableView/types';
import { useFileManagement } from '@/controllers/DATA_API/useFileManagement';
import useAlertStore from '@/stores/alertStore';
import BaseModal from '../baseModal';

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
  defaultViewMode?: 'list' | 'grid';
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
    parentId: number
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
  readOnly?: boolean; // When true, hides create/upload/delete operations (for file selection mode)
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
  defaultViewMode = 'list',
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
  readOnly = false, // Default to false for backward compatibility
}: FileTableViewModalProps): JSX.Element {
  const { t } = useTranslation();
  const [internalOpen, internalSetOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPath, setCurrentPath] = useState('/');
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

  // Use file management hook for search operations
  const fileOps = useFileManagement();

  // Internal state for selected files - FIXED: Remove state duplication to prevent flickering
  const [internalSelectedFiles, setInternalSelectedFiles] =
    useState<FileItem[]>(selectedFiles);

  // Use controlled or uncontrolled state
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setIsOpen =
    controlledSetOpen !== undefined ? controlledSetOpen : internalSetOpen;

  // Refetch files and reset selection when modal opens
  useEffect(() => {
    if (isOpen) {
      queryClient.refetchQueries({
        queryKey: ['useGetFilesV2'],
      });
      // Only reset selection when modal first opens, not on every render
      setInternalSelectedFiles(selectedFiles || []);
    }
  }, [isOpen, queryClient]);
  // Note: selectedFiles is intentionally NOT in dependencies to avoid resetting during selection

  // Handle single file selection (from row click)
  const handleFileSelect = useCallback(
    (file: FileItem) => {
      if (!allowMultiple) {
        setInternalSelectedFiles([file]);
      } else {
        // In multi-select mode, toggle the file
        setInternalSelectedFiles((prevFiles) => {
          const isAlreadySelected = prevFiles.some((f) => f.id === file.id);
          if (isAlreadySelected) {
            return prevFiles.filter((f) => f.id !== file.id);
          } else {
            return [...prevFiles, file];
          }
        });
      }
    },
    [allowMultiple]
  );

  // Handle multiple file selection change (from checkboxes)
  const handleSelectionChange = useCallback(
    (files: FileItem[]) => {
      if (!allowMultiple && files.length > 1) {
        setInternalSelectedFiles([files[files.length - 1]]);
      } else {
        setInternalSelectedFiles(files);
      }
    },
    [allowMultiple]
  );

  // Handle navigation
  const handleNavigation = useCallback((folderId: number, path: string) => {
    setCurrentParentId(folderId);
    setCurrentPath(path);
  }, []);

  // Handle search
  const handleSearch = useCallback(
    async (query: string) => {
      setSearchQuery(query);

      if (!query.trim()) {
        setIsSearching(false);
        setSearchResults([]);
        if (fileTableRef.current) {
          fileTableRef.current.refresh?.();
        }
        return;
      }

      setIsSearching(true);
      try {
        // Use fileOps.getFileList with name parameter for backend search
        const results = await fileOps.getFileList(currentParentId, query);
        setSearchResults(results);
      } catch (error) {
        console.error('Search failed:', error);
        setSearchResults([]);
        setErrorData({
          title: t('fileTableModal.searchFailed'),
          list: [error instanceof Error ? error.message : String(error)],
        });
      }
    },
    [fileOps, currentParentId, t, setErrorData]
  );

  // Default data transformer
  const defaultDataTransformer = useCallback((data: any): FileItem[] => {
    return data.map((item: any) => ({
      id: item.id,
      name: item.name,
      type: item.type === 'folder' ? 'folder' : 'file',
      size: item.file?.size || 0,
      updateTime: item.updateTime || new Date().toISOString().split('T')[0],
      createUser: item.createUser || '-',
      path: item.path,
      suffix: item.suffix,
      hasChildren: item.hasChildren,
      file: item.file,
      tags: item.tags,
    }));
  }, []);

  // Handle create folder
  const handleCreate = useCallback(() => {
    if (fileTableRef.current) {
      fileTableRef.current.startCreateFolder?.();
    }
  }, []);

  // Handle upload
  const handleUpload = useCallback(() => {}, []);

  // Handle upload folder
  const handleUploadFolder = useCallback(() => {}, []);

  // Handle batch delete
  const handleBatchDelete = useCallback(async () => {
    setInternalSelectedFiles((currentFiles) => {
      if (currentFiles.length === 0) {
        setErrorData({
          title: t('fileTableModal.pleaseSelectFilesToDelete'),
        });
        return currentFiles;
      }

      const folderIds = currentFiles
        .filter((f) => f.type === 'folder')
        .map((f) => f.id as number);
      const fileIds = currentFiles
        .filter((f) => f.type === 'file')
        .map((f) => f.id as number);

      (async () => {
        try {
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
        } catch (error) {
          console.error('Delete failed:', error);
          setErrorData({
            title: t('fileTableModal.deleteFailed'),
          });
        }
      })();

      // Clear selection
      return [];
    });
  }, [deleteFolderApi, deleteFileApi, setErrorData, t]);

  // Handle batch download
  const handleBatchDownload = useCallback(() => {
    setInternalSelectedFiles((currentFiles) => {
      if (currentFiles.length === 0) {
        setErrorData({
          title: t('fileTableModal.pleaseSelectFilesToDownload'),
        });
        return currentFiles;
      }

      currentFiles.forEach((file) => {
        if (file.type === 'file' && file.file?.link) {
          window.open(file.file.link, '_blank');
        }
      });

      return currentFiles;
    });
  }, [setErrorData, t]);

  // Handle modal submit with proper validation
  const onSubmit = useCallback(() => {
    setInternalSelectedFiles((currentFiles) => {
      // Check if nothing is selected
      if (currentFiles.length === 0) {
        // If no files selected but we're in folder selection mode,
        // select the current folder
        if (selectableFileTypes?.includes('folder')) {
          const currentFolderItem: FileItem = {
            id: currentParentId,
            name:
              pathHistory[pathHistory.length - 1]?.name ||
              t('fileTableModal.allFiles'),
            type: 'folder',
            path: currentPath,
          };

          if (handleSubmit) {
            handleSubmit([currentFolderItem]);
          }
          return currentFiles;
        }

        // Otherwise show error
        setErrorData({
          title: t('fileTableModal.pleaseSelectAtLeastOneFile'),
        });
        return currentFiles;
      }

      // Submit all selected files (including folders if selected)
      if (handleSubmit) {
        handleSubmit(currentFiles);
      }

      return currentFiles;
    });

    setIsOpen(false);
  }, [
    handleSubmit,
    setErrorData,
    setIsOpen,
    t,
    selectableFileTypes,
    currentParentId,
    currentPath,
    pathHistory,
  ]);

  // Get display title and submitLabel with defaults
  const displayTitle = title || t('fileTableModal.fileManager');
  const displaySubmitLabel = submitLabel || t('fileTableModal.selectFiles');

  return (
    <BaseModal
      size='large-h-full'
      open={!disabled && isOpen}
      setOpen={setIsOpen}
      onSubmit={onSubmit}
    >
      <BaseModal.Trigger asChild>
        {children ? children : <></>}
      </BaseModal.Trigger>

      <BaseModal.Header description={description || null}>
        <span className='flex items-center gap-2 font-medium'>
          <div className='rounded-md bg-muted p-1.5'>
            <ForwardedIconComponent name='FolderOpen' className='h-5 w-5' />
          </div>
          {displayTitle}
        </span>
      </BaseModal.Header>

      <BaseModal.Content overflowHidden>
        <div className='flex h-full flex-col overflow-hidden'>
          <div className='flex flex-1 overflow-hidden'>
            <div className='flex-1 overflow-hidden'>
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
                onFileSelect={handleFileSelect}
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
          dataTestId: 'select-files-modal-button',
        }}
      />
    </BaseModal>
  );
}
