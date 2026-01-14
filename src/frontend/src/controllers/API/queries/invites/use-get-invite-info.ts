import type { InviteInfoResponse, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetInviteInfo {
  inviteCode: string;
}

export const useGetInviteInfoQuery: useQueryFunctionType<
  IGetInviteInfo,
  InviteInfoResponse
> = (options, { inviteCode }) => {
  const { query } = UseRequestProcessor();

  const getInviteInfoFn = async (): Promise<InviteInfoResponse> => {
    const res = await api.get(`/api/v1/rbac/invites/${inviteCode}/info`);
    return res.data;
  };

  const queryResult = query(["useGetInviteInfo", inviteCode], getInviteInfoFn, {
    enabled: !!inviteCode,
    ...options,
  });
  return queryResult;
};
