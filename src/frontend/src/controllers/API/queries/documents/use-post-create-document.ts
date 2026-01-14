import type { DocumentCreate, useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateDocument {
  data: DocumentCreate;
}

interface ICreateDocumentResponse {
  message: string;
  document_ids: number[];
}

export const usePostCreateDocument: useMutationFunctionType<
  ICreateDocumentResponse,
  IPostCreateDocument
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createDocumentFn = async (
    payload: IPostCreateDocument,
  ): Promise<ICreateDocumentResponse> => {
    const res = await api.post(`${getURL("DOCUMENTS")}/`, payload.data);
    return res.data;
  };

  const mutation = mutate(["usePostCreateDocument"], createDocumentFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: [
          "useGetDocuments",
          { search_space_id: variables.data.search_space_id },
        ],
      });
      queryClient.refetchQueries({
        queryKey: ["useGetDocumentTypeCounts", variables.data.search_space_id],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
