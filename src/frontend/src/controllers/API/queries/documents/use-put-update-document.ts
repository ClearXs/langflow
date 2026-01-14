import type {
  DocumentRead,
  DocumentUpdate,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPutUpdateDocument {
  documentId: number;
  data: DocumentUpdate;
}

export const usePutUpdateDocument: useMutationFunctionType<
  DocumentRead,
  IPutUpdateDocument
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateDocumentFn = async (
    payload: IPutUpdateDocument,
  ): Promise<DocumentRead> => {
    const res = await api.put(
      `${getURL("DOCUMENTS")}/${payload.documentId}`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePutUpdateDocument"], updateDocumentFn, {
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.refetchQueries({
        queryKey: [
          "useGetDocuments",
          { search_space_id: data.search_space_id },
        ],
      });
      queryClient.refetchQueries({
        queryKey: ["useGetDocument", variables.documentId],
      });
      options?.onSuccess?.(data, variables, context);
    },
  });

  return mutation;
};
