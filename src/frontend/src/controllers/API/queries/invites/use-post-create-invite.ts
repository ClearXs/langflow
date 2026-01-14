import type {
  SpaceInviteCreate,
  SpaceInviteRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateInvite {
  searchSpaceId: number;
  data: SpaceInviteCreate;
}

export const usePostCreateInvite: useMutationFunctionType<
  SpaceInviteRead,
  IPostCreateInvite
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createInviteFn = async (
    payload: IPostCreateInvite,
  ): Promise<SpaceInviteRead> => {
    const res = await api.post(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/invites`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePostCreateInvite"], createInviteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetInvites"] });
    },
    ...options,
  });

  return mutation;
};
