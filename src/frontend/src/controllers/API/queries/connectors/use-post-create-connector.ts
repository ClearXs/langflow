import type {
  ConnectorCreate,
  ConnectorRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateConnector {
  data: ConnectorCreate;
}

export const usePostCreateConnector: useMutationFunctionType<
  ConnectorRead,
  IPostCreateConnector
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createConnectorFn = async (
    payload: IPostCreateConnector,
  ): Promise<ConnectorRead> => {
    const res = await api.post(`${getURL("CONNECTORS")}/`, payload.data);
    return res.data;
  };

  const mutation = mutate(["usePostCreateConnector"], createConnectorFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: ["useGetConnectors", variables.data.search_space_id],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
