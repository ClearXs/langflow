import type {
  ConnectorRead,
  GetConnectorsParams,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetConnectorsQuery: useQueryFunctionType<
  GetConnectorsParams,
  ConnectorRead[]
> = (options, params) => {
  const { query } = UseRequestProcessor();

  const getConnectorsFn = async (): Promise<ConnectorRead[]> => {
    const queryParams = new URLSearchParams({
      search_space_id: String(params.search_space_id),
    });

    const res = await api.get(`${getURL("CONNECTORS")}?${queryParams}`);
    return res.data;
  };

  const queryResult = query(
    ["useGetConnectors", params.search_space_id],
    getConnectorsFn,
    {
      enabled: !!params.search_space_id,
      ...options,
    },
  );
  return queryResult;
};
