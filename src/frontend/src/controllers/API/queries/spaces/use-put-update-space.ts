import type {
  SpaceRead,
  SpaceUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateSpace {
  spaceId: number;
  data: SpaceUpdate;
}

export const usePutUpdateSpace: useMutationFunctionType<
  SpaceRead,
  IPutUpdateSpace
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateSpaceFn = async (
    payload: IPutUpdateSpace,
  ): Promise<SpaceRead> => {
    const res = await api.put(
      `${getURL("SPACES")}/${payload.spaceId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateSpace"], updateSpaceFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({ queryKey: ["useGetSpaces"] });
      queryClient.refetchQueries({
        queryKey: ["useGetSpace", variables.spaceId],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
