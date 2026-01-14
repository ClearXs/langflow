import type {
  RoleCreate,
  RoleRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateRole {
  searchSpaceId: number;
  data: RoleCreate;
}

export const usePostCreateRole: useMutationFunctionType<
  RoleRead,
  IPostCreateRole
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createRoleFn = async (payload: IPostCreateRole): Promise<RoleRead> => {
    const res = await api.post(
      `/api/v1/rbac/spaces/${payload.searchSpaceId}/roles`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePostCreateRole"], createRoleFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: ["useGetRoles", variables.searchSpaceId],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
