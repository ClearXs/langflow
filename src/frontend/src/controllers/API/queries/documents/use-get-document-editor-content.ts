import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface BlockNoteContent {
  document_id: number;
  title: string;
  blocknote_content: any[];
  doc_type: string;
  created_at: string | null;
  updated_at: string | null;
}

export const useGetDocumentEditorContent: useQueryFunctionType<
  { document_id: number },
  BlockNoteContent
> = (options, params) => {
  const { query } = UseRequestProcessor();

  const getDocumentEditorContentFn = async (): Promise<BlockNoteContent> => {
    const res = await api.get(
      `${getURL("DOCUMENTS")}/${params.document_id}/editor-content`,
    );
    return res.data;
  };

  const queryResult = query(
    ["document-editor-content", params.document_id],
    getDocumentEditorContentFn,
    {
      enabled: !!params.document_id,
      ...options,
    },
  );
  return queryResult;
};
