import type { DeleteRoleResponse, useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteRole {
  searchSpaceId: number;
  roleId: number;
}

export const useDeleteRole: useMutationFunctionType<
  DeleteRoleResponse,
  IDeleteRole
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteRoleFn = async (
    payload: IDeleteRole,
  ): Promise<DeleteRoleResponse> => {
    const res = await api.delete(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/roles/${payload.roleId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteRole"], deleteRoleFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetRoles"] });
    },
    ...options,
  });

  return mutation;
};
