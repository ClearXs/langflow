import type {
  DefaultSystemInstructionsResponse,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetDefaultSystemInstructionsQuery: useQueryFunctionType<
  undefined,
  DefaultSystemInstructionsResponse
> = (options) => {
  const { query } = UseRequestProcessor();

  const getDefaultSystemInstructionsFn =
    async (): Promise<DefaultSystemInstructionsResponse> => {
      const res = await api.get(
        `/api/v1/llm-configs/default-system-instructions`,
      );
      return res.data;
    };

  const queryResult = query(
    ["useGetDefaultSystemInstructions"],
    getDefaultSystemInstructionsFn,
    options,
  );
  return queryResult;
};
