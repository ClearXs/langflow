import type { UserSpaceAccess, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetUserSpaceAccess {
  searchSpaceId: number;
}

export const useGetUserSpaceAccessQuery: useQueryFunctionType<
  IGetUserSpaceAccess,
  UserSpaceAccess
> = (options, { searchSpaceId }) => {
  const { query } = UseRequestProcessor();

  const getUserSpaceAccessFn = async (): Promise<UserSpaceAccess> => {
    const res = await api.get(`/api/v1/rbac/spaces/${searchSpaceId}/access`);
    return res.data;
  };

  const queryResult = query(
    ["useGetUserSpaceAccess", searchSpaceId],
    getUserSpaceAccessFn,
    {
      enabled: !!searchSpaceId,
      ...options,
    },
  );
  return queryResult;
};
