// File item interface matching the API response
export interface FileItem {
  id: number | string;
  parentId?: string;
  name: string;
  path?: string;
  type: "file" | "folder";
  key?: string;
  file?: {
    link?: string;
    domain?: string;
    name?: string;
    originalName?: string;
    attachId?: number;
    size?: number;
  };
  tags?: string[];
  suffix?: string;
  createUser?: string;
  createDept?: string;
  createTime?: string;
  updateUser?: string;
  updateTime?: string;
  status?: number;
  isDeleted?: number;
  tenantId?: string;
  hasChildren?: boolean;
  size?: number;
}

// Table column configuration
export interface TableColumn {
  prop: string;
  label: string;
  sortable?: boolean;
  className?: string;
  width?: string | number;
  style?: React.CSSProperties;
}

// Sort configuration
export interface SortConfig {
  prop: string;
  order: "ascending" | "descending" | null;
}

// Position for context menu
export interface Position {
  x: number;
  y: number;
}

// Component props
export interface FileTableViewProps {
  // Display options
  showSize?: boolean;
  showUpdateTime?: boolean;
  showUser?: boolean;
  selectable?: boolean;
  enableContextMenu?: boolean;
  defaultViewMode?: "list" | "grid";
  showViewModeSwitch?: boolean;
  showBreadcrumb?: boolean;

  // Data options
  files?: FileItem[];
  parentId?: number;
  customRootId?: number;
  currentPath?: string;
  pathHistory?: Array<{ name: string; id: number }>;

  // Behavior options
  keepSelection?: boolean;
  selectableFileTypes?: string[];

  // Custom API functions
  fetchDataApi?: (parentId: number) => Promise<any>;
  dataTransformer?: (data: any) => FileItem[];

  // Custom actions
  customFileActions?: Array<{
    key: string;
    icon: string;
    label: string;
    visible: (file: FileItem) => boolean;
    handler: (file: FileItem) => void;
  }>;

  // Event handlers
  onFileSelect?: (file: FileItem) => void;
  onSelectionChange?: (files: FileItem[]) => void;
  onNavigation?: (parentId: number, path: string) => void;
}
