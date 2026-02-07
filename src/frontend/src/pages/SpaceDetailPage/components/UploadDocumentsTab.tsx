import { AnimatePresence, motion } from "framer-motion";
import { FileText, Loader2, Upload, X } from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { usePostUploadDocuments } from "@/controllers/API/queries/documents";

interface UploadDocumentsTabProps {
  spaceId: number;
  onUploadSuccess?: () => void;
}

interface FileWithPreview {
  file: File;
  id: string;
}

export function UploadDocumentsTab({
  spaceId,
  onUploadSuccess,
}: UploadDocumentsTabProps) {
  const { t } = useTranslation();
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const uploadMutation = usePostUploadDocuments();

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;

    const newFiles: FileWithPreview[] = Array.from(files).map((file) => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
    }));

    setSelectedFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const removeFile = useCallback((id: string) => {
    setSelectedFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast.error(t("spaces.documents.upload.no_files_selected"));
      return;
    }

    try {
      await uploadMutation.mutateAsync({
        files: selectedFiles.map((f) => f.file),
        search_space_id: spaceId,
      });

      toast.success(
        t("spaces.documents.upload.success", { count: selectedFiles.length }),
      );
      setSelectedFiles([]);
      onUploadSuccess?.();
    } catch (error) {
      toast.error(
        t("spaces.documents.upload.error", {
          error: error instanceof Error ? error.message : "Unknown error",
        }),
      );
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative rounded-lg border-2 border-dashed p-8
          transition-colors duration-200
          ${
            isDragging
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-muted-foreground/50"
          }
        `}
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="rounded-full bg-muted p-3">
            <Upload className="h-6 w-6 text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium">
              {t("spaces.documents.upload.drag_drop")}
            </p>
            <p className="text-xs text-muted-foreground">
              {t("spaces.documents.upload.or")}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.multiple = true;
              input.accept =
                ".txt,.pdf,.md,.docx,.xlsx,.pptx,.csv,.json,.xml,.html";
              input.onchange = (e) =>
                handleFileSelect((e.target as HTMLInputElement).files);
              input.click();
            }}
          >
            {t("spaces.documents.upload.browse_files")}
          </Button>
          <p className="text-xs text-muted-foreground">
            {t("spaces.documents.upload.supported_formats")}
          </p>
        </div>
      </div>

      {/* Selected Files List */}
      <AnimatePresence mode="popLayout">
        {selectedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2"
          >
            <p className="text-sm font-medium">
              {t("spaces.documents.upload.selected_files", {
                count: selectedFiles.length,
              })}
            </p>
            <div className="max-h-[200px] space-y-2 overflow-y-auto rounded-lg border p-2">
              {selectedFiles.map((fileWithPreview) => (
                <motion.div
                  key={fileWithPreview.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center justify-between rounded-md bg-muted/50 p-2"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {fileWithPreview.file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(fileWithPreview.file.size)}
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 shrink-0 p-0"
                    onClick={() => removeFile(fileWithPreview.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Button */}
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={handleUpload}
          disabled={selectedFiles.length === 0 || uploadMutation.isPending}
        >
          {uploadMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t("spaces.documents.upload.uploading")}
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              {t("spaces.documents.upload.upload_button", {
                count: selectedFiles.length,
              })}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
