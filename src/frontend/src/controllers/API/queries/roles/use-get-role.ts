import type { RoleRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetRole {
  searchSpaceId: number;
  roleId: number;
}

export const useGetRoleQuery: useQueryFunctionType<IGetRole, RoleRead> = (
  options,
  { searchSpaceId, roleId },
) => {
  const { query } = UseRequestProcessor();

  const getRoleFn = async (): Promise<RoleRead> => {
    const res = await api.get(
      `/api/v1/rbac/spaces/${searchSpaceId}/roles/${roleId}`,
    );
    return res.data;
  };

  const queryResult = query(["useGetRole", searchSpaceId, roleId], getRoleFn, {
    enabled: !!searchSpaceId && !!roleId,
    ...options,
  });
  return queryResult;
};
