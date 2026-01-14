import type {
  MembershipCreate,
  SpaceMembershipRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostAddMember {
  searchSpaceId: number;
  data: MembershipCreate;
}

export const usePostAddMember: useMutationFunctionType<
  SpaceMembershipRead,
  IPostAddMember
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const addMemberFn = async (
    payload: IPostAddMember,
  ): Promise<SpaceMembershipRead> => {
    const res = await api.post(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/members`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePostAddMember"], addMemberFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetMembers"] });
    },
    ...options,
  });

  return mutation;
};
