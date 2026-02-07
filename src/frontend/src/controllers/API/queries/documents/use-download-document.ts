import type { useMutationFunctionType } from "@/types/api";
import { toast } from "sonner";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface DownloadDocumentResponse {
  filename: string;
}

export const useDownloadDocument: useMutationFunctionType<
  number,
  DownloadDocumentResponse
> = (options) => {
  const { mutate } = UseRequestProcessor();

  const downloadDocumentFn = async (
    document_id: number,
  ): Promise<DownloadDocumentResponse> => {
    const response = await api.get(
      `${getURL("DOCUMENTS")}/${document_id}/download`,
      { responseType: "blob" },
    );

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers["content-disposition"];
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
    const filename = filenameMatch
      ? filenameMatch[1]
      : `document-${document_id}.pdf`;

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    return { filename };
  };

  const mutation = mutate(["download-document"], downloadDocumentFn, {
    ...options,
    onError: (error: any, variables, context) => {
      toast.error(
        error.response?.data?.detail || "Failed to download document",
      );

      // Call user-provided onError if exists
      if (options?.onError) {
        options.onError(error, variables, context);
      }
    },
    onSuccess: (data, variables, context) => {
      toast.success(`Downloaded: ${data.filename}`);

      // Call user-provided onSuccess if exists
      if (options?.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
  });

  return mutation;
};
