import type {
  IndexConnectorParams,
  IndexConnectorResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostIndexConnector {
  connectorId: number;
  search_space_id: number;
  params?: IndexConnectorParams;
}

export const usePostIndexConnector: useMutationFunctionType<
  IndexConnectorResponse,
  IPostIndexConnector
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const indexConnectorFn = async (
    payload: IPostIndexConnector,
  ): Promise<IndexConnectorResponse> => {
    const res = await api.post(
      `${getURL("CONNECTORS")}/${payload.connectorId}/index`,
      payload.params || {},
    );
    return res.data;
  };

  const mutation = mutate(["usePostIndexConnector"], indexConnectorFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: ["useGetConnectors", variables.search_space_id],
      });
      queryClient.refetchQueries({
        queryKey: ["useGetConnector", variables.connectorId],
      });
      queryClient.refetchQueries({
        queryKey: [
          "useGetDocuments",
          { search_space_id: variables.search_space_id },
        ],
      });
      queryClient.refetchQueries({
        queryKey: ["useGetDocumentTypeCounts", variables.search_space_id],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
