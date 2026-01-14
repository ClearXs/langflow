export enum PermissionAction {
  READ = "READ",
  WRITE = "WRITE",
  DELETE = "DELETE",
  ADMIN = "ADMIN",
}

export enum ResourceType {
  SPACE = "SPACE",
  DOCUMENT = "DOCUMENT",
  CONNECTOR = "CONNECTOR",
  CHAT = "CHAT",
  NOTE = "NOTE",
}

export interface Permission {
  id: number;
  action: PermissionAction;
  resource_type: ResourceType;
  created_at: string;
}

export interface Role {
  id: number;
  name: string;
  description?: string;
  search_space_id: number;
  permissions: Permission[];
  created_at: string;
  updated_at: string;
  is_default?: boolean;
}

export interface RolesStoreType {
  // State
  roles: Role[];
  permissions: Permission[];
  selectedRoleId: number | null;
  isLoading: boolean;

  // Actions
  setRoles: (roles: Role[]) => void;
  setPermissions: (permissions: Permission[]) => void;
  setSelectedRoleId: (id: number | null) => void;
  setIsLoading: (isLoading: boolean) => void;
  addRole: (role: Role) => void;
  updateRole: (id: number, role: Partial<Role>) => void;
  deleteRole: (id: number) => void;
  resetRoles: () => void;

  // Computed getters
  getSelectedRole: () => Role | null;
  getRolePermissions: (roleId: number) => Permission[];
  hasPermission: (
    roleId: number,
    action: PermissionAction,
    resourceType: ResourceType,
  ) => boolean;
}
