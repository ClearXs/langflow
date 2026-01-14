import type {
  MembershipUpdate,
  SpaceMembershipRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateMember {
  searchSpaceId: number;
  membershipId: number;
  data: MembershipUpdate;
}

export const usePutUpdateMember: useMutationFunctionType<
  SpaceMembershipRead,
  IPutUpdateMember
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateMemberFn = async (
    payload: IPutUpdateMember,
  ): Promise<SpaceMembershipRead> => {
    const res = await api.put(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/members/${payload.membershipId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateMember"], updateMemberFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetMembers"] });
    },
    ...options,
  });

  return mutation;
};
