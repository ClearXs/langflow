import type { DocumentRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetDocument {
  documentId: number;
}

export const useGetDocumentQuery: useQueryFunctionType<
  IGetDocument,
  DocumentRead
> = (options, { documentId }) => {
  const { query } = UseRequestProcessor();

  const getDocumentFn = async (): Promise<DocumentRead> => {
    const res = await api.get(`${getURL("DOCUMENTS")}/${documentId}`);
    return res.data;
  };

  const queryResult = query(["useGetDocument", documentId], getDocumentFn, {
    enabled: !!documentId,
    ...options,
  });
  return queryResult;
};
