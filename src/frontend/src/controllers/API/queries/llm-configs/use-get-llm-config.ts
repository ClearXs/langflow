import type { LLMConfigRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetLLMConfig {
  configId: number;
}

export const useGetLLMConfigQuery: useQueryFunctionType<
  IGetLLMConfig,
  LLMConfigRead
> = (options, { configId }) => {
  const { query } = UseRequestProcessor();

  const getLLMConfigFn = async (): Promise<LLMConfigRead> => {
    const res = await api.get(`/api/v1/llm-configs/${configId}`);
    return res.data;
  };

  const queryResult = query(["useGetLLMConfig", configId], getLLMConfigFn, {
    enabled: !!configId,
    ...options,
  });
  return queryResult;
};
