import { create } from "zustand";
import type {
  PermissionAction,
  ResourceType,
  RolesStoreType,
} from "@/types/zustand/roles";

const useRolesStore = create<RolesStoreType>((set, get) => ({
  // State
  roles: [],
  permissions: [],
  selectedRoleId: null,
  isLoading: false,

  // Actions
  setRoles: (roles) => set({ roles }),

  setPermissions: (permissions) => set({ permissions }),

  setSelectedRoleId: (id) => set({ selectedRoleId: id }),

  setIsLoading: (isLoading) => set({ isLoading }),

  addRole: (role) =>
    set((state) => ({
      roles: [...state.roles, role],
    })),

  updateRole: (id, updatedRole) =>
    set((state) => ({
      roles: state.roles.map((role) =>
        role.id === id ? { ...role, ...updatedRole } : role,
      ),
    })),

  deleteRole: (id) =>
    set((state) => ({
      roles: state.roles.filter((role) => role.id !== id),
      selectedRoleId: state.selectedRoleId === id ? null : state.selectedRoleId,
    })),

  resetRoles: () =>
    set({
      roles: [],
      permissions: [],
      selectedRoleId: null,
      isLoading: false,
    }),

  // Computed getters
  getSelectedRole: () => {
    const { selectedRoleId, roles } = get();
    if (!selectedRoleId) return null;
    return roles.find((role) => role.id === selectedRoleId) ?? null;
  },

  getRolePermissions: (roleId: number) => {
    const { roles } = get();
    const role = roles.find((r) => r.id === roleId);
    return role?.permissions ?? [];
  },

  hasPermission: (
    roleId: number,
    action: PermissionAction,
    resourceType: ResourceType,
  ) => {
    const { roles } = get();
    const role = roles.find((r) => r.id === roleId);
    if (!role) return false;

    return role.permissions.some(
      (permission) =>
        permission.action === action &&
        permission.resource_type === resourceType,
    );
  },
}));

export default useRolesStore;
