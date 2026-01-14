import type {
  LLMConfigCreate,
  LLMConfigRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const usePostCreateLLMConfig: useMutationFunctionType<
  LLMConfigRead,
  LLMConfigCreate
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createLLMConfigFn = async (
    payload: LLMConfigCreate,
  ): Promise<LLMConfigRead> => {
    const res = await api.post(`/api/v1/llm-configs`, payload);
    return res.data;
  };

  const mutation = mutate(["usePostCreateLLMConfig"], createLLMConfigFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetLLMConfigs"] });
    },
    ...options,
  });

  return mutation;
};
