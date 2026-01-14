import type {
  LLMConfigRead,
  LLMConfigUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateLLMConfig {
  configId: number;
  data: LLMConfigUpdate;
}

export const usePutUpdateLLMConfig: useMutationFunctionType<
  LLMConfigRead,
  IPutUpdateLLMConfig
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateLLMConfigFn = async (
    payload: IPutUpdateLLMConfig,
  ): Promise<LLMConfigRead> => {
    const res = await api.put(
      `/api/v1/llm-configs/${payload.configId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateLLMConfig"], updateLLMConfigFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetLLMConfigs"] });
      queryClient.refetchQueries({ queryKey: ["useGetLLMConfig"] });
    },
    ...options,
  });

  return mutation;
};
