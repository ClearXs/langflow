import type {
  DeleteMembershipResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteLeaveSpace {
  searchSpaceId: number;
}

export const useDeleteLeaveSpace: useMutationFunctionType<
  DeleteMembershipResponse,
  IDeleteLeaveSpace
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const leaveSpaceFn = async (
    payload: IDeleteLeaveSpace,
  ): Promise<DeleteMembershipResponse> => {
    const res = await api.delete(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/members/me`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteLeaveSpace"], leaveSpaceFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetMembers"] });
      queryClient.refetchQueries({ queryKey: ["useGetSpaces"] });
    },
    ...options,
  });

  return mutation;
};
