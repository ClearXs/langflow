import type {
  InviteUpdate,
  SpaceInviteRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateInvite {
  searchSpaceId: number;
  inviteId: number;
  data: InviteUpdate;
}

export const usePutUpdateInvite: useMutationFunctionType<
  SpaceInviteRead,
  IPutUpdateInvite
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateInviteFn = async (
    payload: IPutUpdateInvite,
  ): Promise<SpaceInviteRead> => {
    const res = await api.put(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/invites/${payload.inviteId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateInvite"], updateInviteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetInvites"] });
    },
    ...options,
  });

  return mutation;
};
