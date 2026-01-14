import type {
  DocumentRead,
  GetDocumentsParams,
  PaginatedResponse,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetDocumentsQuery: useQueryFunctionType<
  GetDocumentsParams,
  PaginatedResponse<DocumentRead>
> = (options, params) => {
  const { query } = UseRequestProcessor();

  const getDocumentsFn = async (): Promise<PaginatedResponse<DocumentRead>> => {
    const queryParams = new URLSearchParams({
      search_space_id: String(params.search_space_id),
      ...(params.document_types && {
        document_types: params.document_types.join(","),
      }),
      page: String(params.page ?? 1),
      page_size: String(params.page_size ?? 10),
    });

    const res = await api.get(`${getURL("DOCUMENTS")}?${queryParams}`);
    return res.data;
  };

  const queryResult = query(["useGetDocuments", params], getDocumentsFn, {
    enabled: !!params.search_space_id,
    ...options,
  });
  return queryResult;
};
