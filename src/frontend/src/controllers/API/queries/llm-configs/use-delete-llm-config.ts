import type {
  DeleteLLMConfigResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteLLMConfig {
  configId: number;
}

export const useDeleteLLMConfig: useMutationFunctionType<
  DeleteLLMConfigResponse,
  IDeleteLLMConfig
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteLLMConfigFn = async (
    payload: IDeleteLLMConfig,
  ): Promise<DeleteLLMConfigResponse> => {
    const res = await api.delete(`/api/v1/llm-configs/${payload.configId}`);
    return res.data;
  };

  const mutation = mutate(["useDeleteLLMConfig"], deleteLLMConfigFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetLLMConfigs"] });
    },
    ...options,
  });

  return mutation;
};
