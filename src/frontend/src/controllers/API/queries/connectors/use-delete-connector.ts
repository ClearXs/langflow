import type {
  DeleteConnectorResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteConnector {
  connectorId: number;
  search_space_id: number;
}

export const useDeleteConnector: useMutationFunctionType<
  DeleteConnectorResponse,
  IDeleteConnector
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteConnectorFn = async (
    payload: IDeleteConnector,
  ): Promise<DeleteConnectorResponse> => {
    const res = await api.delete(
      `${getURL("CONNECTORS")}/${payload.connectorId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteConnector"], deleteConnectorFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: ["useGetConnectors", variables.search_space_id],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
