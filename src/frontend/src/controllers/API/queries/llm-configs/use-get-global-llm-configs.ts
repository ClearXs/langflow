import type { GlobalLLMConfigRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetGlobalLLMConfigsQuery: useQueryFunctionType<
  undefined,
  GlobalLLMConfigRead[]
> = (options) => {
  const { query } = UseRequestProcessor();

  const getGlobalLLMConfigsFn = async (): Promise<GlobalLLMConfigRead[]> => {
    const res = await api.get(`/api/v1/llm-configs/global`);
    return res.data;
  };

  const queryResult = query(
    ["useGetGlobalLLMConfigs"],
    getGlobalLLMConfigsFn,
    options,
  );
  return queryResult;
};
