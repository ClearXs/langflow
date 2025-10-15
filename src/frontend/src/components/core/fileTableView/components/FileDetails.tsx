import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileIcon } from "./FileIcon";
import type { FileItem } from "../types";

interface FileDetailsProps {
  file?: FileItem | null;
  currentPath?: string;
  isVisible?: boolean;
  selectList?: FileItem[];
  onToggle?: () => void;
}

export function FileDetails({
  file,
  currentPath = "/",
  isVisible = true,
  selectList = [],
  onToggle,
}: FileDetailsProps) {
  const { t } = useTranslation();

  // Ensure selectList is always an array
  const safeSelectList = useMemo(() => {
    return Array.isArray(selectList) ? selectList : [];
  }, [selectList]);

  // Calculate folder count
  const folderCount = useMemo(() => {
    return safeSelectList.filter((item) => item.type === "folder").length;
  }, [safeSelectList]);

  // Calculate file count
  const fileCount = useMemo(() => {
    return safeSelectList.filter((item) => item.type === "file").length;
  }, [safeSelectList]);

  // Calculate total size
  const totalSize = useMemo(() => {
    return safeSelectList.reduce((total, item) => {
      return total + (item.type === "file" ? (item.file?.size || item.size || 0) : 0);
    }, 0);
  }, [safeSelectList]);

  // Format file size
  const formatFileSize = (size?: number) => {
    if (!size || size === 0) return "0 B";

    const units = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + " " + units[i];
  };

  // Format file type
  const formatFileType = (type: string) => {
    switch (type) {
      case "folder":
        return t("fileDetails.folder");
      case "image":
        return t("fileDetails.image");
      default:
        return t("fileDetails.file");
    }
  };

  if (!isVisible) {
    return (
      <div className="w-8 border-l bg-background">
        <div className="flex h-12 items-center justify-center">
          <Button variant="ghost" size="icon" onClick={onToggle}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h3 className="text-sm font-medium">{t("fileDetails.title")}</h3>
        <Button variant="ghost" size="icon" onClick={onToggle}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="h-[calc(100%-3rem)] overflow-y-auto p-4">
        {/* Empty state */}
        {safeSelectList.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 text-6xl opacity-20">📁</div>
            <p className="text-sm text-muted-foreground">{t("fileDetails.selectFileToView")}</p>
          </div>
        )}

        {/* Multiple selection */}
        {safeSelectList.length > 1 && (
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 rounded-xl bg-muted p-8">
              <div className="text-6xl">📦</div>
            </div>
            <h4 className="mb-4 text-sm font-medium">
              {t("fileDetails.selectedCount", { count: safeSelectList.length })}
            </h4>
            <div className="w-full space-y-2 text-left text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t("fileDetails.folders")}：</span>
                <span>{t("fileDetails.count", { count: folderCount })}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t("fileDetails.files")}：</span>
                <span>{t("fileDetails.count", { count: fileCount })}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t("fileDetails.totalSize")}：</span>
                <span>{formatFileSize(totalSize)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Single selection */}
        {safeSelectList.length === 1 && file && (
          <div className="space-y-4">
            {/* Preview */}
            <div className="flex justify-center">
              <div className="flex h-32 w-32 items-center justify-center rounded-xl bg-muted p-4">
                <FileIcon fileName={file.name} fileType={file.type} size={64} />
              </div>
            </div>

            {/* Info */}
            <div className="space-y-3">
              <h4 className="break-all text-sm font-medium">{file.name}</h4>

              <div className="space-y-2 text-xs">
                <div className="flex">
                  <span className="w-20 text-muted-foreground">{t("fileDetails.type")}：</span>
                  <span>{formatFileType(file.type)}</span>
                </div>

                <div className="flex">
                  <span className="w-20 text-muted-foreground">{t("fileDetails.size")}：</span>
                  <span>
                    {file.type === "folder" ? "-" : formatFileSize(file.file?.size || file.size)}
                  </span>
                </div>

                <div className="flex">
                  <span className="w-20 text-muted-foreground">{t("fileDetails.updateTime")}：</span>
                  <span>{file.updateTime || "-"}</span>
                </div>

                <div className="flex">
                  <span className="w-20 text-muted-foreground">{t("fileDetails.creator")}：</span>
                  <span>{file.createUser || "-"}</span>
                </div>

                <div className="flex">
                  <span className="w-20 text-muted-foreground">{t("fileDetails.path")}：</span>
                  <span className="flex-1 break-all">{file.path || currentPath}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
