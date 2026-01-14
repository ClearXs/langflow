import type { PermissionInfo, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetPermissionsQuery: useQueryFunctionType<
  undefined,
  PermissionInfo[]
> = (options) => {
  const { query } = UseRequestProcessor();

  const getPermissionsFn = async (): Promise<PermissionInfo[]> => {
    const res = await api.get(`/api/v1/rbac/permissions`);
    return res.data;
  };

  const queryResult = query(["useGetPermissions"], getPermissionsFn, options);
  return queryResult;
};
