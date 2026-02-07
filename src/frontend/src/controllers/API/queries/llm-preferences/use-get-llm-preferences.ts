import type {
  LLMPreferencesRead,
  UseQueryOptions,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetLLMPreferences {
  spaceId: number;
}

export const useGetLLMPreferences: useQueryFunctionType<
  IGetLLMPreferences,
  LLMPreferencesRead
> = (params, options?) => {
  const { query } = UseRequestProcessor();

  const getLLMPreferencesFn = async () => {
    const res = await api.get<LLMPreferencesRead>(
      `/api/v1/spaces/${params.spaceId}/llm-preferences`,
    );
    return res.data;
  };

  const queryResult = query(
    ["useGetLLMPreferences", params.spaceId],
    getLLMPreferencesFn,
    {
      enabled: !!params.spaceId,
      ...options,
    } as UseQueryOptions<LLMPreferencesRead, any>,
  );

  return queryResult;
};
