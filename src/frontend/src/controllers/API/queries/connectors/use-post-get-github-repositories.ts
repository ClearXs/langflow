import type {
  GetGitHubRepositoriesParams,
  GetGitHubRepositoriesResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const usePostGetGitHubRepositories: useMutationFunctionType<
  GetGitHubRepositoriesResponse,
  GetGitHubRepositoriesParams
> = (options?) => {
  const { mutate } = UseRequestProcessor();

  const getGitHubRepositoriesFn = async (
    payload: GetGitHubRepositoriesParams,
  ): Promise<GetGitHubRepositoriesResponse> => {
    const res = await api.post(
      `${getURL("CONNECTORS")}/github/repositories`,
      payload,
    );
    return res.data;
  };

  const mutation = mutate(
    ["usePostGetGitHubRepositories"],
    getGitHubRepositoriesFn,
    options,
  );

  return mutation;
};
