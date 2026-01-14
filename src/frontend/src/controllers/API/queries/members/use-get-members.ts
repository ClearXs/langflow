import type { SpaceMembershipRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetMembers {
  searchSpaceId: number;
}

export const useGetMembersQuery: useQueryFunctionType<
  IGetMembers,
  SpaceMembershipRead[]
> = (options, { searchSpaceId }) => {
  const { query } = UseRequestProcessor();

  const getMembersFn = async (): Promise<SpaceMembershipRead[]> => {
    const res = await api.get(`/api/v1/rbac/spaces/${searchSpaceId}/members`);
    return res.data;
  };

  const queryResult = query(["useGetMembers", searchSpaceId], getMembersFn, {
    enabled: !!searchSpaceId,
    ...options,
  });
  return queryResult;
};
