import type {
  ConnectorRead,
  ConnectorUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateConnector {
  connectorId: number;
  data: ConnectorUpdate;
}

export const usePutUpdateConnector: useMutationFunctionType<
  ConnectorRead,
  IPutUpdateConnector
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateConnectorFn = async (
    payload: IPutUpdateConnector,
  ): Promise<ConnectorRead> => {
    const res = await api.put(
      `${getURL("CONNECTORS")}/${payload.connectorId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateConnector"], updateConnectorFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: ["useGetConnectors", data.search_space_id],
      });
      queryClient.refetchQueries({
        queryKey: ["useGetConnector", variables.connectorId],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
