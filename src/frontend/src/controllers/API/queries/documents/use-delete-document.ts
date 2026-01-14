import type {
  DeleteDocumentResponse,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteDocument {
  documentId: number;
  search_space_id: number;
}

export const useDeleteDocument: useMutationFunctionType<
  DeleteDocumentResponse,
  IDeleteDocument
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteDocumentFn = async (
    payload: IDeleteDocument,
  ): Promise<DeleteDocumentResponse> => {
    const res = await api.delete(
      `${getURL("DOCUMENTS")}/${payload.documentId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteDocument"], deleteDocumentFn, {
    ...options,
    onSuccess: (data, variables, context) => {
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
