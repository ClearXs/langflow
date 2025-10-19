import { X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { FileItem } from "@/components/core/fileTableView/types";
import { Button } from "@/components/ui/button";
import useDataAPI from "@/controllers/DATA_API/api";
import FileTableViewModal from "@/modals/fileTableViewModal";
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

  const dataApi = useDataAPI();

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
  const allowedExtensions =
    fileTypes && fileTypes.length > 0
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

  const handleSelectFiles = (files: FileItem[]) => {
    setSelectedFiles(files);

    const fileNames = files.map((f) => f.name);
    const filePaths = files.map((f) => f.path || f.name);

    handleOnNewValue({
      value: isList ? fileNames : fileNames[0] || "",
      file_path: isList ? filePaths : filePaths[0] || "",
    });
  };

  const handleRemoveFile = (fileId: string | number) => {
    const newFiles = selectedFiles.filter((f) => f.id !== fileId);
    handleSelectFiles(newFiles);
  };

  const isDisabled = disabled;
  const hasFiles = selectedFiles.length > 0;

  return (
    <div className="w-full">
      <div className="flex flex-col gap-2">
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
          selectableFileTypes={allowedExtensions}
          allowMultiple={isList ?? false}
          title={t("fileInput.modalTitle")}
          description={
            allowedExtensions
              ? t("fileInput.modalDescriptionWithTypes", {
                  types: allowedExtensions.join(", "),
                })
              : t("fileInput.modalDescription")
          }
          submitLabel={t("fileInput.selectFiles")}
          showNavBar={true}
          showFileDetails={true}
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
            {hasFiles && !isList
              ? t("fileInput.changeFile")
              : hasFiles && isList
                ? t("fileInput.addMore")
                : t("fileInput.selectFile")}
          </Button>
        </FileTableViewModal>

        {/* File Count Display */}
        {hasFiles && isList && (
          <div className="text-xs text-muted-foreground">
            {t("fileInput.filesSelected", { count: selectedFiles.length })}
          </div>
        )}
      </div>
    </div>
  );
}
