import { Upload, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { FileItem } from "@/components/core/fileTableView/types";
import { Button } from "@/components/ui/button";
import useDataAPI from "@/controllers/DATA_API/api";
import { useFileManagement } from "@/controllers/DATA_API/useFileManagement";
import FileTableViewModal from "@/modals/fileTableViewModal";
import useAlertStore from "@/stores/alertStore";
import { cn } from "@/utils/utils";
import type { FileComponentType, InputProps } from "../../types";

export default function FileTableInputComponent({
  value,
  file_path,
  handleOnNewValue,
  disabled,
  fileTypes,
  isList,
  editNode = false,
  id,
}: InputProps<string | string[], FileComponentType>): JSX.Element {
  const { t } = useTranslation();
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const dataApi = useDataAPI();
  const fileOps = useFileManagement();
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);

  // Check if folder-only mode (fileTypes contains "folder")
  const folderOnly = fileTypes && fileTypes.includes("folder");

  // Use useCallback to memoize the fetchFiles function and prevent infinite loops
  const fetchFiles = useCallback(
    async (
      parentId: string = "0",
    ): Promise<{ data: FileItem[]; total: number }> => {
      return await dataApi.get(
        `/data-construction/resource-folder/lazy-tree-resources?parentId=${parentId}`,
      );
    },
    [dataApi],
  );

  // Parse file types for filtering
  // If fileTypes contains "folder", this is folder-only mode
  const allowedExtensions =
    fileTypes && fileTypes.length > 0 && !folderOnly
      ? fileTypes.map((type) => (type.startsWith(".") ? type.slice(1) : type))
      : undefined;

  // Initialize selected files from props
  useEffect(() => {
    if (!file_path) {
      setSelectedFiles([]);
      return;
    }

    const paths = Array.isArray(file_path) ? file_path : [file_path];
    const names = Array.isArray(value) ? value : [value];

    const files: FileItem[] = paths
      .map((path, index) => {
        if (!path) return null;

        return {
          id: path,
          name: names[index] || path.split("/").pop() || "",
          path: path,
          type: "file" as const,
        };
      })
      .filter((f): f is FileItem => f !== null);

    setSelectedFiles(files);
  }, [file_path, value]);

  // Download file by ID and save to temporary location
  const downloadAndSaveFile = useCallback(
    async (fileItem: FileItem): Promise<string> => {
      try {
        const fileId =
          typeof fileItem.id === "string" ? parseInt(fileItem.id) : fileItem.id;
        const { blob, filename } = await fileOps.downloadFileById(fileId);

        // Create a File object from Blob
        const file = new File([blob], filename, { type: blob.type });

        // Create FormData and upload to temporary location
        const formData = new FormData();
        formData.append("file", file);

        // Upload to a temporary location (assuming there's a temp upload endpoint)
        // For now, we'll use the browser's temporary storage
        const url = URL.createObjectURL(blob);

        return url;
      } catch (error) {
        console.error("Failed to download file:", error);
        throw error;
      }
    },
    [fileOps],
  );

  const handleSelectFiles = useCallback(
    async (files: FileItem[]) => {
      // Filter to folders only if in folder-only mode
      const filteredFiles = folderOnly
        ? files.filter((f) => f.type === "folder")
        : files;

      setSelectedFiles(filteredFiles);

      try {
        const fileNames = filteredFiles.map((f) => f.name);
        const fileIds = filteredFiles.map((f) => f.id.toString());

        handleOnNewValue({
          value: isList ? fileNames : fileNames[0] || "",
          file_path: isList ? fileIds : fileIds[0] || "",
        });
      } catch (error) {
        setErrorData({
          title: t("fileInput.downloadFailed"),
          list: [error instanceof Error ? error.message : String(error)],
        });
      }
    },
    [folderOnly, isList, handleOnNewValue, setErrorData, t],
  );

  const handleRemoveFile = useCallback(
    (fileId: string | number) => {
      const newFiles = selectedFiles.filter((f) => f.id !== fileId);
      handleSelectFiles(newFiles);
    },
    [selectedFiles, handleSelectFiles],
  );

  // Handle drag and drop
  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragging(true);
      }
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled) return;

      const droppedFiles = Array.from(e.dataTransfer.files);

      // Filter files by allowed extensions
      const validFiles = droppedFiles.filter((file) => {
        if (!allowedExtensions) return true;
        const ext = file.name.split(".").pop()?.toLowerCase();
        return ext && allowedExtensions.includes(ext);
      });

      if (validFiles.length === 0) {
        setErrorData({
          title: t("fileInput.invalidFileType"),
          list: allowedExtensions
            ? [
                t("fileInput.allowedTypes", {
                  types: allowedExtensions.join(", "),
                }),
              ]
            : [t("fileInput.noValidFiles")],
        });
        return;
      }

      // If not list mode and already has file, show error
      if (!isList && selectedFiles.length > 0) {
        setErrorData({
          title: t("fileInput.singleFileOnly"),
          list: [t("fileInput.removeExistingFile")],
        });
        return;
      }

      // Upload files
      setIsUploading(true);
      try {
        const uploadedFiles: FileItem[] = [];

        for (const file of validFiles) {
          // Upload to root folder (parentId = 0)
          const result = await fileOps.uploadFile(0, file);

          if (result.data) {
            uploadedFiles.push({
              id: result.data.id,
              name: file.name,
              path: result.data.path || file.name,
              type: "file",
              file: result.data.file,
            });
          }
        }

        if (uploadedFiles.length > 0) {
          const newFiles = isList
            ? [...selectedFiles, ...uploadedFiles]
            : uploadedFiles.slice(0, 1);

          await handleSelectFiles(newFiles);

          setSuccessData({
            title: t("fileInput.filesUploaded", {
              count: uploadedFiles.length,
            }),
          });
        }
      } catch (error) {
        setErrorData({
          title: t("fileInput.uploadFailed"),
          list: [error instanceof Error ? error.message : String(error)],
        });
      } finally {
        setIsUploading(false);
      }
    },
    [
      disabled,
      allowedExtensions,
      isList,
      selectedFiles,
      handleSelectFiles,
      setErrorData,
      setSuccessData,
      t,
    ],
  );

  const isDisabled = disabled || isUploading;
  const hasFiles = selectedFiles.length > 0;

  return (
    <div className="w-full">
      <div
        className="flex flex-col gap-2"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Drag and Drop Zone */}
        {isDragging && (
          <div className="absolute inset-0 z-50 flex items-center justify-center rounded-lg border-2 border-dashed border-primary bg-primary/10 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2 text-center">
              <Upload className="h-8 w-8 text-primary" />
              <p className="text-sm font-medium text-primary">
                {t("fileInput.dropFilesHere")}
              </p>
              {allowedExtensions && (
                <p className="text-xs text-muted-foreground">
                  {t("fileInput.allowedTypes", {
                    types: allowedExtensions.join(", "),
                  })}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Selected Files Display */}
        {hasFiles && (
          <div className="flex max-h-44 flex-col gap-1.5 overflow-y-auto rounded-md border border-border bg-background p-2">
            {selectedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between gap-2 rounded-sm border border-border bg-muted/50 px-3 py-1.5 text-sm hover:bg-muted"
              >
                <span className="flex-1 truncate" title={file.name}>
                  {file.name}
                </span>
                {!isDisabled && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 shrink-0 hover:bg-destructive/10"
                    onClick={() => handleRemoveFile(file.id)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* File Selection Modal */}
        <FileTableViewModal
          fetchDataApi={fetchFiles}
          handleSubmit={handleSelectFiles}
          selectableFileTypes={folderOnly ? ["folder"] : allowedExtensions}
          allowMultiple={isList ?? false}
          title={
            folderOnly
              ? t("fileInput.selectFolderTitle")
              : t("fileInput.modalTitle")
          }
          description={
            folderOnly
              ? t("fileInput.selectFolderDescription")
              : allowedExtensions
                ? t("fileInput.modalDescriptionWithTypes", {
                    types: allowedExtensions.join(", "),
                  })
                : t("fileInput.modalDescription")
          }
          submitLabel={
            folderOnly
              ? t("fileInput.selectFolder")
              : t("fileInput.selectFiles")
          }
          showNavBar={true}
          showFileDetails={!folderOnly}
          readOnly={true}
        >
          <Button
            data-testid={`file-table-input-${id}`}
            disabled={isDisabled}
            variant={hasFiles && !isList ? "outline" : "default"}
            className={cn(
              "w-full",
              hasFiles &&
                !isList &&
                "border-accent-emerald-foreground text-accent-emerald-foreground hover:bg-accent-emerald-foreground/10",
            )}
          >
            {isUploading ? (
              <>
                <Upload className="mr-2 h-4 w-4 animate-spin" />
                {t("fileInput.uploading")}
              </>
            ) : hasFiles && !isList ? (
              t("fileInput.changeFile")
            ) : hasFiles && isList ? (
              t("fileInput.addMore")
            ) : (
              t("fileInput.selectFile")
            )}
          </Button>
        </FileTableViewModal>

        {/* File Count Display or Drag Hint */}
        {hasFiles && isList ? (
          <div className="text-xs text-muted-foreground">
            {t("fileInput.filesSelected", { count: selectedFiles.length })}
          </div>
        ) : (
          !hasFiles && (
            <div className="text-xs text-center text-muted-foreground">
              {t("fileInput.dragDropHint")}
            </div>
          )
        )}
      </div>
    </div>
  );
}
