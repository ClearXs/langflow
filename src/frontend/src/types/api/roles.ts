// RBAC API Type Definitions
// Based on backend schemas from src/backend/base/langflow/api/v1/rbac.py

export interface PermissionInfo {
  value: string;
  name: string;
  category: string;
}

export interface PermissionsListResponse {
  permissions: PermissionInfo[];
}

export interface RoleRead {
  id: number;
  name: string;
  description: string | null;
  search_space_id: number;
  permissions: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoleCreate {
  name: string;
  description?: string | null;
  permissions: string[];
  is_default?: boolean;
}

export interface RoleUpdate {
  name?: string;
  description?: string | null;
  permissions?: string[];
  is_default?: boolean;
}

export interface DeleteRoleResponse {
  message: string;
}
