import type {
  DocumentTypeCount,
  GetDocumentTypeCountsParams,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetDocumentTypeCountsQuery: useQueryFunctionType<
  GetDocumentTypeCountsParams,
  DocumentTypeCount[]
> = (options, params) => {
  const { query } = UseRequestProcessor();

  const getDocumentTypeCountsFn = async (): Promise<DocumentTypeCount[]> => {
    const queryParams = new URLSearchParams({
      search_space_id: String(params.search_space_id),
    });

    const res = await api.get(
      `${getURL("DOCUMENTS")}/type-counts?${queryParams}`,
    );
    return res.data;
  };

  const queryResult = query(
    ["useGetDocumentTypeCounts", params.search_space_id],
    getDocumentTypeCountsFn,
    {
      enabled: !!params.search_space_id,
      ...options,
    },
  );
  return queryResult;
};
