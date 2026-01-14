import type {
  RoleRead,
  RoleUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateRole {
  searchSpaceId: number;
  roleId: number;
  data: RoleUpdate;
}

export const usePutUpdateRole: useMutationFunctionType<
  RoleRead,
  IPutUpdateRole
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateRoleFn = async (payload: IPutUpdateRole): Promise<RoleRead> => {
    const res = await api.put(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/roles/${payload.roleId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateRole"], updateRoleFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetRoles"] });
      queryClient.refetchQueries({ queryKey: ["useGetRole"] });
    },
    ...options,
  });

  return mutation;
};
