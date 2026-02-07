import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { lazy, Suspense, useState, useEffect } from "react";
import {
  useGetDocumentEditorContent,
  useSaveDocument,
} from "@/controllers/API/queries/documents";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";

// Lazy load to avoid SSR issues
const BlockNoteEditor = lazy(
  () => import("@/components/documents/BlockNoteEditor"),
);

export default function DocumentEditorPage() {
  const { t } = useTranslation();
  const { spaceId, documentId } = useParams<{
    spaceId: string;
    documentId: string;
  }>();
  const navigate = useNavigate();

  const [editorContent, setEditorContent] = useState<any[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch document content
  const {
    data: documentData,
    isLoading,
    error,
  } = useGetDocumentEditorContent(
    { enabled: !!documentId },
    { document_id: Number(documentId) },
  );

  // Save mutation
  const saveDocument = useSaveDocument();

  // Check if document is editable (not PDF, etc.)
  const isEditable = documentData?.doc_type !== "pdf";

  // Initialize editor content when data loads
  useEffect(() => {
    if (documentData?.blocknote_content) {
      setEditorContent(documentData.blocknote_content);
    }
  }, [documentData]);

  const handleSave = async () => {
    if (!documentId || !isEditable) return;

    try {
      await saveDocument.mutateAsync({
        document_id: Number(documentId),
        blocknote_content: editorContent,
      });
      toast.success(t("documents.editor.saveSuccess"));
      setHasChanges(false);
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleBack = () => {
    if (hasChanges) {
      if (!confirm(t("documents.editor.unsavedChanges"))) {
        return;
      }
    }
    navigate(`/spaces/${spaceId}/documents`);
  };

  const handleContentChange = (content: any[]) => {
    setEditorContent(content);
    setHasChanges(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-destructive">{t("documents.editor.loadError")}</p>
        <Button onClick={handleBack} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          {t("common.back")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0 flex-1">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t("common.back")}
          </Button>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold truncate">{documentData?.title}</h2>
            <p className="text-sm text-muted-foreground truncate">
              {t("documents.editor.lastUpdated")}:{" "}
              {documentData?.updated_at
                ? new Date(documentData.updated_at).toLocaleString()
                : t("common.never")}
            </p>
          </div>
        </div>

        {isEditable && (
          <Button
            onClick={handleSave}
            disabled={!hasChanges || saveDocument.isPending}
            className="flex-shrink-0"
          >
            {saveDocument.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            {t("common.save")}
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isEditable ? (
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            }
          >
            <BlockNoteEditor
              initialContent={documentData?.blocknote_content || []}
              onChange={handleContentChange}
            />
          </Suspense>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <p className="text-muted-foreground">
              {t("documents.editor.notEditable", { type: documentData?.doc_type?.toUpperCase() || "PDF" })}
            </p>
            <Button
              variant="outline"
              onClick={() => {
                // Trigger download
                window.open(`/api/v1/documents/${documentId}/download`, '_blank');
              }}
            >
              {t("documents.actions.download")}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
