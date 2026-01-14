import type {
  SpaceCreate,
  SpaceRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateSpace {
  data: SpaceCreate;
}

export const usePostCreateSpace: useMutationFunctionType<
  SpaceRead,
  IPostCreateSpace
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createSpaceFn = async (
    payload: IPostCreateSpace,
  ): Promise<SpaceRead> => {
    const res = await api.post(`${getURL("SPACES")}/`, payload.data);
    return res.data;
  };

  const mutation = mutate(["usePostCreateSpace"], createSpaceFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({ queryKey: ["useGetSpaces"] });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
