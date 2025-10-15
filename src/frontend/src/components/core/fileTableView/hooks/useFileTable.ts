import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import type { FileItem, TableColumn, Position, FileTableViewProps } from "../types";

export function useFileTable(props: FileTableViewProps) {
  const [fileList, setFileList] = useState<FileItem[]>(props.files || []);
  const [selectedItems, setSelectedItems] = useState<FileItem[]>([]);
  const [currentParentId, setCurrentParentId] = useState<number>(props.parentId || 0);
  const [currentPath, setCurrentPath] = useState<string>(props.currentPath || "/");
  const [pathHistory, setPathHistory] = useState<Array<{ name: string; id: number }>>(
    props.pathHistory || []
  );
  const [hoveredRow, setHoveredRow] = useState<FileItem | null>(null);
  const [contextMenuVisible, setContextMenuVisible] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState<Position>({ x: 0, y: 0 });
  const [contextMenuFile, setContextMenuFile] = useState<FileItem | null>(null);
  const [sortConfig, setSortConfig] = useState({ prop: "", order: null as "ascending" | "descending" | null });

  // Folder creation and rename states
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [fileToRename, setFileToRename] = useState<FileItem | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);
  const newFolderInputRef = useRef<HTMLInputElement>(null);

  // Fetch files
  const fetchFiles = useCallback(async () => {
    try {
      if (props.fetchDataApi) {
        const response = await props.fetchDataApi(currentParentId);
        if (response && response.data && response.data.data) {
          const transformer = props.dataTransformer || defaultDataTransformer;
          setFileList(transformer(response.data.data));
        }
      }
    } catch (error) {
      console.error("Failed to fetch files", error);
    }
  }, [currentParentId, props.fetchDataApi, props.dataTransformer]);

  // FIXED: Auto-fetch files when currentParentId changes
  useEffect(() => {
    if (props.fetchDataApi && !props.files) {
      fetchFiles();
    }
  }, [currentParentId, fetchFiles, props.fetchDataApi, props.files]);

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

  // Navigate to folder
  const navigateToFolder = useCallback(
    (folder: FileItem) => {
      setCurrentPath(`${currentPath}${folder.name}/`);
      setCurrentParentId(folder.id as number);
      setPathHistory([...pathHistory, { name: folder.name, id: folder.id as number }]);

      if (!props.keepSelection) {
        setSelectedItems([]);
      }

      props.onNavigation?.(folder.id as number, `${currentPath}${folder.name}/`);
    },
    [currentPath, pathHistory, props.keepSelection, props.onNavigation]
  );

  // Navigate to root
  const navigateToRoot = useCallback(() => {
    setCurrentPath("/");
    setCurrentParentId(props.customRootId || 0);
    setPathHistory([]);

    if (!props.keepSelection) {
      setSelectedItems([]);
    }

    props.onNavigation?.(props.customRootId || 0, "/");
  }, [props.customRootId, props.keepSelection, props.onNavigation]);

  // Navigate to path
  const navigateToPath = useCallback(
    (index: number, pathSegments: string[]) => {
      const path = "/" + pathSegments.slice(0, index + 1).join("/") + "/";
      setCurrentPath(path);

      if (!props.keepSelection) {
        setSelectedItems([]);
      }

      if (index >= 0 && index < pathHistory.length) {
        setCurrentParentId(pathHistory[index].id);
        setPathHistory(pathHistory.slice(0, index + 1));
      } else {
        setCurrentParentId(props.customRootId || 0);
        setPathHistory([]);
      }

      props.onNavigation?.(currentParentId, path);
    },
    [pathHistory, currentParentId, props.keepSelection, props.customRootId, props.onNavigation]
  );

  // Start creating folder
  const startCreateFolder = useCallback(() => {
    setIsCreatingFolder(true);
    setNewFolderName("新建文件夹");
    setTimeout(() => {
      newFolderInputRef.current?.focus();
      newFolderInputRef.current?.select();
    }, 0);
  }, []);

  // Confirm create folder
  const confirmCreateFolder = useCallback(
    async (createFolderApi?: (parentId: number, name: string) => Promise<any>) => {
      if (!newFolderName.trim()) {
        console.warn("Folder name cannot be empty");
        return;
      }

      try {
        if (createFolderApi) {
          const response = await createFolderApi(currentParentId, newFolderName.trim());
          if (response && response.data && response.data.success) {
            await fetchFiles();
          }
        } else {
          // Add temp folder to list for demo
          const tempFolder: FileItem = {
            id: `temp-${Date.now()}`,
            name: newFolderName.trim(),
            type: "folder",
            createTime: new Date().toISOString(),
            updateTime: new Date().toISOString(),
          };
          setFileList([...fileList, tempFolder]);
        }
      } catch (error) {
        console.error("Failed to create folder", error);
      } finally {
        setIsCreatingFolder(false);
        setNewFolderName("");
      }
    },
    [newFolderName, currentParentId, fileList, fetchFiles]
  );

  // Cancel create folder
  const cancelCreateFolder = useCallback(() => {
    setIsCreatingFolder(false);
    setNewFolderName("");
  }, []);

  // Start rename
  const startRename = useCallback((file: FileItem) => {
    if (file.type !== "folder") {
      console.warn("Only folders can be renamed");
      return;
    }

    setFileToRename(file);
    setNewFolderName(file.name);
    setIsRenaming(true);

    setTimeout(() => {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }, 0);
  }, []);

  // Confirm rename
  const confirmRename = useCallback(
    async (renameApi?: (id: number, name: string, parentId: number) => Promise<any>) => {
      if (!newFolderName.trim()) {
        console.warn("Folder name cannot be empty");
        return;
      }

      if (!fileToRename) return;

      try {
        if (renameApi) {
          const response = await renameApi(
            fileToRename.id as number,
            newFolderName.trim(),
            currentParentId
          );
          if (response && response.data && response.data.success) {
            await fetchFiles();
          }
        } else {
          // Update folder name in list for demo
          setFileList(
            fileList.map((item) =>
              item.id === fileToRename.id ? { ...item, name: newFolderName.trim() } : item
            )
          );
        }
      } catch (error) {
        console.error("Failed to rename", error);
      } finally {
        setIsRenaming(false);
        setFileToRename(null);
        setNewFolderName("");
      }
    },
    [newFolderName, fileToRename, currentParentId, fileList, fetchFiles]
  );

  // Cancel rename
  const cancelRename = useCallback(() => {
    setIsRenaming(false);
    setFileToRename(null);
    setNewFolderName("");
  }, []);

  // Format file size
  const formatFileSize = (size?: number): string => {
    if (size === undefined || size === null) return "-";
    if (size === 0 || size === -1) return "0 B";

    const units = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + " " + units[i];
  };

  // Check if file is selectable
  const isFileSelectable = useCallback(
    (file: FileItem): boolean => {
      if (!props.selectableFileTypes || props.selectableFileTypes.length === 0) {
        return true;
      }

      return props.selectableFileTypes.some((allowedType) => {
        // Match type field
        if (file.type && file.type.toLowerCase() === allowedType.toLowerCase()) {
          return true;
        }

        // Match extension
        if (allowedType.startsWith(".")) {
          const extension = allowedType.toLowerCase();
          if (file.name) {
            const nameExtension = "." + (file.name.split(".").pop() || "").toLowerCase();
            if (nameExtension === extension) {
              return true;
            }
          }
          if (file.suffix) {
            const suffixLower = file.suffix.toLowerCase();
            if (suffixLower === extension || suffixLower === extension.substring(1)) {
              return true;
            }
          }
        }

        // Match suffix
        if (file.suffix && file.suffix.toLowerCase() === allowedType.toLowerCase()) {
          return true;
        }

        return false;
      });
    },
    [props.selectableFileTypes]
  );

  // Table columns configuration
  const columns = useMemo<TableColumn[]>(() => {
    const cols: TableColumn[] = [
      {
        prop: "name",
        label: "名称",
        sortable: true,
        className: "name-column",
      },
    ];
    if (props.showUpdateTime) {
      cols.push({
        prop: "updateTime",
        label: "修改时间",
        sortable: true,
        style: { width: "20%", flexShrink: 0 },
      });
    }
    if (props.showSize) {
      cols.push({
        prop: "size",
        label: "大小",
        sortable: true,
        style: { width: "10%", flexShrink: 0 },
      });
    }
    if (props.showUser) {
      cols.push({
        prop: "createUser",
        label: "创建者",
        style: { width: "10%", flexShrink: 0 },
      });
    }
    return cols;
  }, [props.showUpdateTime, props.showSize, props.showUser]);

  // Event handlers
  const handleRowClick = useCallback(
    (row: FileItem) => {
      if (!props.keepSelection) {
        setSelectedItems([row]);
      }
      props.onFileSelect?.(row);
    },
    [props.keepSelection, props.onFileSelect]
  );

  const handleRowDblClick = useCallback(
    (row: FileItem) => {
      if (row.type === "folder") {
        navigateToFolder(row);
      }
    },
    [navigateToFolder]
  );

  const handleSelectionChange = useCallback(
    (selection: FileItem[]) => {
      setSelectedItems(selection);
      props.onSelectionChange?.(selection);
    },
    [props.onSelectionChange]
  );

  const handleSortChange = useCallback((config: { prop: string; order: "ascending" | "descending" | null }) => {
    setSortConfig(config);
  }, []);

  const handleContextMenu = useCallback((event: React.MouseEvent, file: FileItem) => {
    if (!props.enableContextMenu) return;

    setContextMenuPosition({
      x: event.clientX,
      y: event.clientY,
    });
    setContextMenuFile(file);
    setContextMenuVisible(true);
  }, [props.enableContextMenu]);

  const handleMouseEnter = useCallback((row: FileItem) => {
    setHoveredRow(row);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoveredRow(null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedItems([]);
  }, []);

  return {
    // State
    fileList,
    setFileList,
    selectedItems,
    currentParentId,
    setCurrentParentId,
    currentPath,
    pathHistory,
    hoveredRow,
    contextMenuVisible,
    setContextMenuVisible,
    contextMenuPosition,
    contextMenuFile,
    sortConfig,
    columns,

    // Folder creation and rename states
    isCreatingFolder,
    isRenaming,
    fileToRename,
    newFolderName,
    setNewFolderName,
    renameInputRef,
    newFolderInputRef,

    // Methods
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

    // Folder operations
    startCreateFolder,
    confirmCreateFolder,
    cancelCreateFolder,
    startRename,
    confirmRename,
    cancelRename,
  };
}
