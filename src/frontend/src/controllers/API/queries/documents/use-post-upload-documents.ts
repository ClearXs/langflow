import type { FileUploadResponse, useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostUploadDocuments {
  files: File[];
  search_space_id: number;
}

export const usePostUploadDocuments: useMutationFunctionType<
  FileUploadResponse,
  IPostUploadDocuments
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const uploadDocumentsFn = async (
    payload: IPostUploadDocuments,
  ): Promise<FileUploadResponse> => {
    const formData = new FormData();
    payload.files.forEach((file) => formData.append("files", file));
    formData.append("search_space_id", String(payload.search_space_id));

    const res = await api.post(`${getURL("DOCUMENTS")}/fileupload`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return res.data;
  };

  const mutation = mutate(["usePostUploadDocuments"], uploadDocumentsFn, {
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
