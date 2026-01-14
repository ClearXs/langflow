import type { LLMPreferencesRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetLLMPreferences {
  spaceId: number;
}

export const useGetLLMPreferencesQuery: useQueryFunctionType<
  IGetLLMPreferences,
  LLMPreferencesRead
> = (options, { spaceId }) => {
  const { query } = UseRequestProcessor();

  const getLLMPreferencesFn = async (): Promise<LLMPreferencesRead> => {
    const res = await api.get(`${getURL("SPACES")}/${spaceId}/llm-preferences`);
    return res.data;
  };

  const queryResult = query(
    ["useGetLLMPreferences", spaceId],
    getLLMPreferencesFn,
    {
      enabled: !!spaceId,
      ...options,
    },
  );
  return queryResult;
};
