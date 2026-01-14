import type { ConnectorRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetConnector {
  connectorId: number;
}

export const useGetConnectorQuery: useQueryFunctionType<
  IGetConnector,
  ConnectorRead
> = (options, { connectorId }) => {
  const { query } = UseRequestProcessor();

  const getConnectorFn = async (): Promise<ConnectorRead> => {
    const res = await api.get(`${getURL("CONNECTORS")}/${connectorId}`);
    return res.data;
  };

  const queryResult = query(["useGetConnector", connectorId], getConnectorFn, {
    enabled: !!connectorId,
    ...options,
  });
  return queryResult;
};
