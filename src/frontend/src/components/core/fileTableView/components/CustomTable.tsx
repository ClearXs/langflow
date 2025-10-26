import { ArrowDown, ArrowUp, Grid3x3, List } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/utils/utils";
import type { FileItem, SortConfig, TableColumn } from "../types";

interface CustomTableProps {
  data: FileItem[];
  columns: TableColumn[];
  viewMode: "list" | "grid";
  selectable?: boolean;
  selectedItems?: FileItem[];
  sortConfig?: SortConfig;
  isFileSelectable?: (file: FileItem) => boolean;
  onRowClick?: (row: FileItem, event: React.MouseEvent) => void;
  onRowDblClick?: (row: FileItem) => void;
  onSelectionChange?: (selection: FileItem[]) => void;
  onSortChange?: (config: SortConfig) => void;
  onContextMenu?: (event: React.MouseEvent, row: FileItem) => void;
  onRowMouseEnter?: (row: FileItem) => void;
  onRowMouseLeave?: (row: FileItem) => void;
  renderCell?: (column: string, row: FileItem) => React.ReactNode;
  renderGridItem?: (row: FileItem) => React.ReactNode;
}

export function CustomTable({
  data,
  columns,
  viewMode,
  selectable = false,
  selectedItems = [],
  sortConfig = { prop: "", order: null },
  isFileSelectable = () => true,
  onRowClick,
  onRowDblClick,
  onSelectionChange,
  onSortChange,
  onContextMenu,
  onRowMouseEnter,
  onRowMouseLeave,
  renderCell,
  renderGridItem,
}: CustomTableProps) {
  const { t } = useTranslation();
  // FIXED: Remove internal state to prevent flickering - use props directly
  const [currentSort, setCurrentSort] = useState<SortConfig>(sortConfig);

  // Sorted data
  const sortedData = useMemo(() => {
    if (!currentSort.prop || !currentSort.order) {
      return data;
    }

    return [...data].sort((a, b) => {
      const aValue = a[currentSort.prop as keyof FileItem];
      const bValue = b[currentSort.prop as keyof FileItem];

      if (currentSort.order === "ascending") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }, [data, currentSort]);

  // Selection helpers
  const isSelected = (row: FileItem) => {
    return selectedItems.some((item) => item.id === row.id);
  };

  const selectableFiles = useMemo(() => {
    return data.filter((file) => isFileSelectable(file));
  }, [data, isFileSelectable]);

  const isAllSelected = useMemo(() => {
    if (selectableFiles.length === 0) return false;
    return selectableFiles.every((file) =>
      selectedItems.some((item) => item.id === file.id),
    );
  }, [selectableFiles, selectedItems]);

  const isIndeterminate = useMemo(() => {
    if (selectableFiles.length === 0) return false;
    const selectedCount = selectableFiles.filter((file) =>
      selectedItems.some((item) => item.id === file.id),
    ).length;
    return selectedCount > 0 && selectedCount < selectableFiles.length;
  }, [selectableFiles, selectedItems]);

  // Event handlers
  const handleRowClick = (row: FileItem, event: React.MouseEvent) => {
    onRowClick?.(row, event);
  };

  const handleRowDblClick = (row: FileItem) => {
    onRowDblClick?.(row);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const newSelected = [...selectedItems];
      selectableFiles.forEach((file) => {
        if (!newSelected.some((item) => item.id === file.id)) {
          newSelected.push(file);
        }
      });
      onSelectionChange?.(newSelected);
    } else {
      const selectableIds = new Set(selectableFiles.map((f) => f.id));
      const newSelected = selectedItems.filter(
        (item) => !selectableIds.has(item.id),
      );
      onSelectionChange?.(newSelected);
    }
  };

  const handleCheckboxChange = (checked: boolean, row: FileItem) => {
    if (!isFileSelectable(row)) return;

    const newSelected = checked
      ? [...selectedItems, row]
      : selectedItems.filter((item) => item.id !== row.id);

    onSelectionChange?.(newSelected);
  };

  const handleSort = (column: TableColumn) => {
    if (!column.sortable) return;

    let order: "ascending" | "descending" | null = "ascending";
    if (currentSort.prop === column.prop) {
      if (currentSort.order === "ascending") {
        order = "descending";
      } else if (currentSort.order === "descending") {
        order = null;
      }
    }

    const newSort = { prop: column.prop, order };
    setCurrentSort(newSort);
    onSortChange?.(newSort);
  };

  // List view
  if (viewMode === "list") {
    return (
      <div className="flex h-full w-full flex-col">
        {/* Header */}
        <div className="flex items-center border-b bg-background px-2">
          {selectable && (
            <div className="flex w-12 items-center justify-center">
              <Checkbox
                checked={isAllSelected}
                onCheckedChange={handleSelectAll}
                disabled={selectableFiles.length === 0}
                className={cn(
                  isIndeterminate && "data-[state=checked]:bg-primary/50",
                )}
              />
            </div>
          )}
          {columns.map((column) => (
            <div
              key={column.prop}
              className={cn(
                "flex flex-1 items-center gap-2 px-3 py-3 text-sm font-medium cursor-pointer hover:bg-muted/50",
                column.className,
              )}
              style={column.style}
              onClick={() => handleSort(column)}
            >
              <span>{column.label}</span>
              {column.sortable && currentSort.prop === column.prop && (
                <span className="flex items-center">
                  {currentSort.order === "ascending" ? (
                    <ArrowUp className="h-4 w-4" />
                  ) : (
                    <ArrowDown className="h-4 w-4" />
                  )}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto">
          {sortedData.map((row) => {
            const isDisabled = !isFileSelectable(row);
            const isFolder = row.type === "folder";
            // Folders should always be clickable for navigation, even if checkbox is disabled
            const isClickable = !isDisabled || isFolder;

            return (
              <div
                key={row.id}
                className={cn(
                  "flex items-center border-b px-2 min-h-[50px]",
                  isClickable && "hover:bg-muted/50 cursor-pointer",
                  isDisabled && !isFolder && "opacity-50 cursor-not-allowed",
                  isSelected(row) && !isDisabled && "bg-accent",
                )}
                onClick={(e) => isClickable && handleRowClick(row, e)}
                onDoubleClick={() => handleRowDblClick(row)}
                onContextMenu={(e) => {
                  if (isDisabled && !isFolder) return;
                  e.preventDefault();
                  onContextMenu?.(e, row);
                }}
                onMouseEnter={() => isClickable && onRowMouseEnter?.(row)}
                onMouseLeave={() => isClickable && onRowMouseLeave?.(row)}
              >
                {selectable && (
                  <div className="flex w-12 items-center justify-center">
                    <Checkbox
                      checked={isSelected(row)}
                      onCheckedChange={(checked) =>
                        handleCheckboxChange(Boolean(checked), row)
                      }
                      disabled={!isFileSelectable(row)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}
                {columns.map((column) => (
                  <div
                    key={column.prop}
                    className={cn(
                      "flex flex-1 items-center px-3 py-2 text-sm overflow-hidden text-ellipsis whitespace-nowrap",
                      column.className,
                    )}
                    style={column.style}
                  >
                    {renderCell
                      ? renderCell(column.prop, row)
                      : String(row[column.prop as keyof FileItem] || "-")}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Grid view
  return (
    <div className="flex h-full w-full flex-col">
      {/* Grid header with select all */}
      {selectable && (
        <div className="flex items-center gap-2 border-b bg-background px-4 py-3">
          <Checkbox
            checked={isAllSelected}
            onCheckedChange={handleSelectAll}
            disabled={selectableFiles.length === 0}
            className={cn(
              isIndeterminate && "data-[state=checked]:bg-primary/50",
            )}
          />
          <span className="text-sm">{t("fileTableModal.selectAll")}</span>
        </div>
      )}

      {/* Grid container */}
      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {sortedData.map((row) => {
            const isDisabled = !isFileSelectable(row);
            const isFolder = row.type === "folder";
            // Folders should always be clickable for navigation, even if checkbox is disabled
            const isClickable = !isDisabled || isFolder;

            return (
              <div
                key={row.id}
                className={cn(
                  "relative flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors",
                  isClickable && "hover:bg-muted/50 cursor-pointer",
                  isDisabled && !isFolder && "opacity-50 cursor-not-allowed",
                  isSelected(row) && !isDisabled && "bg-accent border-primary",
                )}
                onClick={(e) => isClickable && handleRowClick(row, e)}
                onDoubleClick={() => handleRowDblClick(row)}
                onContextMenu={(e) => {
                  if (isDisabled && !isFolder) return;
                  e.preventDefault();
                  onContextMenu?.(e, row);
                }}
                onMouseEnter={() => isClickable && onRowMouseEnter?.(row)}
                onMouseLeave={() => isClickable && onRowMouseLeave?.(row)}
              >
                {selectable && (
                  <div className="absolute left-2 top-2">
                    <Checkbox
                      checked={isSelected(row)}
                      onCheckedChange={(checked) =>
                        handleCheckboxChange(Boolean(checked), row)
                      }
                      disabled={!isFileSelectable(row)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}
                {renderGridItem ? (
                  renderGridItem(row)
                ) : (
                  <>
                    <div className="text-4xl">
                      {row.type === "folder" ? "📁" : "📄"}
                    </div>
                    <div className="w-full truncate text-center text-sm">
                      {row.name}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
