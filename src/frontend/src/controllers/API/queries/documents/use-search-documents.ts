import type {
  DocumentRead,
  PaginatedResponse,
  SearchDocumentsParams,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useSearchDocumentsQuery: useQueryFunctionType<
  SearchDocumentsParams,
  PaginatedResponse<DocumentRead>
> = (options, params) => {
  const { query } = UseRequestProcessor();

  const searchDocumentsFn = async (): Promise<
    PaginatedResponse<DocumentRead>
  > => {
    const queryParams = new URLSearchParams({
      search_space_id: String(params.search_space_id),
      title: params.title,
      page: String(params.page ?? 0),
      page_size: String(params.page_size ?? 50),
    });

    const res = await api.get(`${getURL("DOCUMENTS")}/search?${queryParams}`);
    return res.data;
  };

  const queryResult = query(["useSearchDocuments", params], searchDocumentsFn, {
    enabled: !!params.search_space_id && !!params.title,
    ...options,
  });
  return queryResult;
};
