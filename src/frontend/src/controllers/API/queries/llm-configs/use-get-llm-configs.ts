import type { LLMConfigRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetLLMConfigs {
  searchSpaceId: number;
}

export const useGetLLMConfigsQuery: useQueryFunctionType<
  IGetLLMConfigs,
  LLMConfigRead[]
> = (options, { searchSpaceId }) => {
  const { query } = UseRequestProcessor();

  const getLLMConfigsFn = async (): Promise<LLMConfigRead[]> => {
    const res = await api.get(
      `/api/v1/llm-configs?search_space_id=${searchSpaceId}`,
    );
    return res.data;
  };

  const queryResult = query(
    ["useGetLLMConfigs", searchSpaceId],
    getLLMConfigsFn,
    {
      enabled: !!searchSpaceId,
      ...options,
    },
  );
  return queryResult;
};
