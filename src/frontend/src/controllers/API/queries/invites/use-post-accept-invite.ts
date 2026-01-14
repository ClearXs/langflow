import type {
  InviteAcceptRequest,
  InviteAcceptResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const usePostAcceptInvite: useMutationFunctionType<
  InviteAcceptResponse,
  InviteAcceptRequest
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const acceptInviteFn = async (
    payload: InviteAcceptRequest,
  ): Promise<InviteAcceptResponse> => {
    const res = await api.post(`/api/v1/rbac/invites/accept`, payload);
    return res.data;
  };

  const mutation = mutate(["usePostAcceptInvite"], acceptInviteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetSpaces"] });
      queryClient.refetchQueries({ queryKey: ["useGetMembers"] });
    },
    ...options,
  });

  return mutation;
};
