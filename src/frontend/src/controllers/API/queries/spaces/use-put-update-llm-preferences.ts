import type {
  LLMPreferencesRead,
  LLMPreferencesUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
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
      `${getURL("SPACES")}/${payload.spaceId}/llm-preferences`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(
    ["usePutUpdateLLMPreferences"],
    updateLLMPreferencesFn,
    {
      ...options,
      onSuccess: (data, variables, context) => {
        queryClient.refetchQueries({
          queryKey: ["useGetLLMPreferences", variables.spaceId],
        });
        options?.onSuccess?.(data, variables, context);
      },
    },
  );

  return mutation;
};
