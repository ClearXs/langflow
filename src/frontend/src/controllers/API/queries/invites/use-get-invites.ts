import type { SpaceInviteRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetInvites {
  searchSpaceId: number;
}

export const useGetInvitesQuery: useQueryFunctionType<
  IGetInvites,
  SpaceInviteRead[]
> = (options, { searchSpaceId }) => {
  const { query } = UseRequestProcessor();

  const getInvitesFn = async (): Promise<SpaceInviteRead[]> => {
    const res = await api.get(`/api/v1/rbac/spaces/${searchSpaceId}/invites`);
    return res.data;
  };

  const queryResult = query(["useGetInvites", searchSpaceId], getInvitesFn, {
    enabled: !!searchSpaceId,
    ...options,
  });
  return queryResult;
};
