import { useEffect, useMemo, useState } from "react";
import { List, Grid3x3, ChevronRight, Download, Trash2, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/utils";
import { FileIcon } from "./components/FileIcon";
import { CustomTable } from "./components/CustomTable";
import { useFileTable } from "./hooks/useFileTable";
import type { FileTableViewProps, FileItem } from "./types";

export function FileTableView(props: FileTableViewProps) {
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

  const {
    fileList,
    setFileList,
    selectedItems,
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
      console.warn("Cannot download folder");
      return;
    }
    if (file.file?.link) {
      window.open(file.file.link, "_blank");
    }
  };

  // Handle delete
  const handleDelete = (file: FileItem) => {
    console.log("Delete file:", file);
    // Implement delete logic here
  };

  // Handle preview
  const handlePreview = (file: FileItem) => {
    if (file.type === "folder") return;
    console.log("Preview file:", file);
    // Implement preview logic here
  };

  // Render cell content
  const renderCell = (columnProp: string, row: FileItem) => {
    switch (columnProp) {
      case "name":
        return (
          <div className="flex items-center gap-2">
            <FileIcon fileName={row.name} fileType={row.type} size={24} />
            <span
              className={cn(
                "truncate",
                row.type === "folder" && "font-medium text-primary cursor-pointer hover:underline"
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
            {/* Action buttons on hover */}
            {enableContextMenu && hoveredRow?.id === row.id && (
              <div className="ml-auto flex items-center gap-1">
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
                    handleDelete(row);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        );

      case "updateTime":
        return <span>{row.updateTime || "-"}</span>;

      case "size":
        return <span>{row.type === "folder" ? "-" : formatFileSize(row.file?.size || row.size)}</span>;

      case "createUser":
        return <span>{row.createUser || "-"}</span>;

      default:
        return <span>{String(row[columnProp as keyof FileItem] || "-")}</span>;
    }
  };

  // Render grid item
  const renderGridItem = (row: FileItem) => {
    return (
      <>
        <FileIcon fileName={row.name} fileType={row.type} size={48} />
        <div className="w-full truncate text-center text-sm font-medium">{row.name}</div>
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
      {/* Breadcrumb navigation */}
      {showBreadcrumb && (
        <div className="flex items-center justify-between border-b px-4 py-2">
          <div className="flex items-center gap-1 text-sm">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={navigateToRoot}
            >
              全部文件
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
      <div className="flex-1 overflow-hidden">
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
    </div>
  );
}

// Re-export types
export type { FileItem, FileTableViewProps } from "./types";
