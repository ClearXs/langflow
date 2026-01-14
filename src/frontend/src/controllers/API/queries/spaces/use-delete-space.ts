import type { DeleteSpaceResponse, useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteSpace {
  spaceId: number;
}

export const useDeleteSpace: useMutationFunctionType<
  DeleteSpaceResponse,
  IDeleteSpace
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteSpaceFn = async (
    payload: IDeleteSpace,
  ): Promise<DeleteSpaceResponse> => {
    const res = await api.delete(`${getURL("SPACES")}/${payload.spaceId}`);
    return res.data;
  };

  const mutation = mutate(["useDeleteSpace"], deleteSpaceFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({ queryKey: ["useGetSpaces"] });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
