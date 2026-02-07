import type {
  LLMPreferencesRead,
  LLMPreferencesUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateLLMPreferences {
  spaceId: number;
  data: LLMPreferencesUpdate;
}

export const usePutUpdateLLMPreferences: useMutationFunctionType<
  LLMPreferencesRead,
  IPutUpdateLLMPreferences
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateLLMPreferencesFn = async (
    payload: IPutUpdateLLMPreferences,
  ): Promise<LLMPreferencesRead> => {
    const res = await api.put(
      `/api/v1/spaces/${payload.spaceId}/llm-preferences`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(
    ["usePutUpdateLLMPreferences"],
    updateLLMPreferencesFn,
    {
      onSettled: () => {
        queryClient.refetchQueries({ queryKey: ["useGetLLMPreferences"] });
      },
      ...options,
    },
  );

  return mutation;
};
