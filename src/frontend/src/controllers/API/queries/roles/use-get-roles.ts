import type { RoleRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetRoles {
  searchSpaceId: number;
}

export const useGetRolesQuery: useQueryFunctionType<IGetRoles, RoleRead[]> = (
  options,
  { searchSpaceId },
) => {
  const { query } = UseRequestProcessor();

  const getRolesFn = async (): Promise<RoleRead[]> => {
    const res = await api.get(`/api/v1/rbac/spaces/${searchSpaceId}/roles`);
    return res.data;
  };

  const queryResult = query(["useGetRoles", searchSpaceId], getRolesFn, {
    enabled: !!searchSpaceId,
    ...options,
  });
  return queryResult;
};
