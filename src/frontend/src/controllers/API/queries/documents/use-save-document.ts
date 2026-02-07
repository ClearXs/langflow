import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface SaveDocumentParams {
  document_id: number;
  blocknote_content: any[];
  title?: string;
}

interface SaveDocumentResponse {
  success: boolean;
  document_id: number;
  updated_at: string | null;
}

export const useSaveDocument: useMutationFunctionType<
  SaveDocumentParams,
  SaveDocumentResponse
> = (options) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const saveDocumentFn = async (
    params: SaveDocumentParams,
  ): Promise<SaveDocumentResponse> => {
    const res = await api.post(
      `${getURL("DOCUMENTS")}/${params.document_id}/save`,
      {
        blocknote_content: params.blocknote_content,
        title: params.title,
      },
    );
    return res.data;
  };

  const mutation = mutate(
    ["save-document"],
    saveDocumentFn,
    {
      ...options,
      onSuccess: (data, variables, context) => {
        // Invalidate editor content query
        queryClient.invalidateQueries({
          queryKey: ["document-editor-content", variables.document_id],
        });
        // Invalidate documents list
        queryClient.invalidateQueries({ queryKey: ["useGetDocuments"] });

        // Call user-provided onSuccess if exists
        if (options?.onSuccess) {
          options.onSuccess(data, variables, context);
        }
      },
    },
  );

  return mutation;
};
