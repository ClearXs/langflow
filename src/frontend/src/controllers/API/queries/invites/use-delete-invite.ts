import type {
  DeleteInviteResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteInvite {
  searchSpaceId: number;
  inviteId: number;
}

export const useDeleteInvite: useMutationFunctionType<
  DeleteInviteResponse,
  IDeleteInvite
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteInviteFn = async (
    payload: IDeleteInvite,
  ): Promise<DeleteInviteResponse> => {
    const res = await api.delete(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/invites/${payload.inviteId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteInvite"], deleteInviteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetInvites"] });
    },
    ...options,
  });

  return mutation;
};
