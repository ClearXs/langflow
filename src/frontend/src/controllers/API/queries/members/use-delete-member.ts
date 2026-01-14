import type {
  DeleteMembershipResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteMember {
  searchSpaceId: number;
  membershipId: number;
}

export const useDeleteMember: useMutationFunctionType<
  DeleteMembershipResponse,
  IDeleteMember
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteMemberFn = async (
    payload: IDeleteMember,
  ): Promise<DeleteMembershipResponse> => {
    const res = await api.delete(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/members/${payload.membershipId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteMember"], deleteMemberFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetMembers"] });
    },
    ...options,
  });

  return mutation;
};
