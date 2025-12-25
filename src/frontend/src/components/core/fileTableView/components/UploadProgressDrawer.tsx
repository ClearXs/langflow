/**
 * UploadProgressDrawer Component
 *
 * Drawer panel showing real-time upload progress for folders and files
 * Features:
 * - Overall progress bar
 * - Folder creation status list (collapsible)
 * - File upload progress list with individual progress bars
 * - Pause/Resume/Retry/Cancel controls
 */

import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  Loader2,
  Pause,
  Play,
  X,
  XCircle,
} from "lucide-react";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/utils/utils";
import type { FolderNode } from "../hooks/useFolderUpload";
import type { UploadTask } from "../hooks/useUploadQueue";

// ==================== Types ====================

export interface UploadProgressDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  folders: FolderNode[];
  tasks: UploadTask[];
  activeUploads: number;
  totalCompleted: number;
  totalFailed: number;
  isRunning: boolean;
  onPause: () => void;
  onResume: () => void;
  onCancel: (taskId: string) => void;
  onRetry: (taskId: string) => void;
}

// ==================== Helper Functions ====================

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(2) + " " + units[i];
}

// ==================== Component ====================

export function UploadProgressDrawer({
  isOpen,
  onClose,
  folders,
  tasks,
  activeUploads,
  totalCompleted,
  totalFailed,
  isRunning,
  onPause,
  onResume,
  onCancel,
  onRetry,
}: UploadProgressDrawerProps) {
  const { t } = useTranslation();
  const [isFoldersExpanded, setIsFoldersExpanded] = useState(true);

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.status === "completed").length;
  const overallProgress =
    totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay - Higher z-index to cover everything including sidebar */}
      <div className="fixed inset-0 bg-black/20 z-[9998]" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-96 bg-background border-l shadow-lg z-[9999] flex flex-col">
        {/* Header */}
        <div className="border-b p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-lg">
              {t("fileTableModal.uploadProgress")}
            </h3>

            {/* Right side button group */}
            <div className="flex items-center gap-2">
              {/* Pause/Resume button (icon only) */}
              {isRunning ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onPause}
                  className="h-8 w-8 p-0"
                  title={t("fileTableModal.pause")}
                >
                  <Pause className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onResume}
                  className="h-8 w-8 p-0"
                  disabled={
                    tasks.length === 0 ||
                    tasks.every(
                      (t) => t.status === "completed" || t.status === "error",
                    )
                  }
                  title={t("fileTableModal.resume")}
                >
                  <Play className="h-4 w-4" />
                </Button>
              )}

              {/* Close button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>
                {completedTasks} / {totalTasks} {t("fileTableModal.files")}
              </span>
              <span>{Math.round(overallProgress)}%</span>
            </div>
            <Progress value={overallProgress} className="h-2" />
            <div className="flex gap-4 text-xs text-muted-foreground">
              <span>
                {activeUploads} {t("fileTableModal.activeUploads")}
              </span>
              {totalFailed > 0 && (
                <span className="text-red-500">
                  {totalFailed} {t("fileTableModal.failedUploads")}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">
            {/* Folders Section */}
            {folders.length > 0 && (
              <div className="space-y-2">
                <button
                  onClick={() => setIsFoldersExpanded(!isFoldersExpanded)}
                  className="flex items-center gap-2 text-sm font-medium w-full hover:bg-accent/50 rounded p-2 transition-colors"
                >
                  {isFoldersExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <FolderOpen className="h-4 w-4" />
                  <span>
                    {t("fileTableModal.folders")} ({folders.length})
                  </span>
                </button>

                {isFoldersExpanded && (
                  <div className="space-y-1">
                    {folders.map((folder, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-sm p-2 rounded hover:bg-accent/30"
                        style={{ paddingLeft: `${folder.depth * 12 + 8}px` }}
                      >
                        {folder.status === "created" && (
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                        )}
                        {folder.status === "creating" && (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-500 flex-shrink-0" />
                        )}
                        {folder.status === "error" && (
                          <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                        )}
                        {folder.status === "pending" && (
                          <Folder className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        )}
                        <span className="flex-1 truncate" title={folder.name}>
                          {folder.name}
                        </span>
                        {folder.error && (
                          <span
                            className="text-xs text-red-500 truncate"
                            title={folder.error}
                          >
                            {folder.error}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Files Section */}
            {tasks.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium px-2">
                  {t("fileTableModal.files")} ({tasks.length})
                </div>
                <div className="space-y-2">
                  {tasks.map((task) => (
                    <div
                      key={task.id}
                      className={cn(
                        "p-3 rounded-lg border space-y-2 transition-colors",
                        task.status === "error" &&
                          "border-red-200 bg-red-50 dark:bg-red-950/20",
                        task.status === "completed" &&
                          "border-green-200 bg-green-50 dark:bg-green-950/20",
                        task.status === "uploading" &&
                          "border-blue-200 bg-blue-50 dark:bg-blue-950/20",
                        task.status === "waiting" &&
                          "border-gray-200 bg-gray-50 dark:bg-gray-900/20",
                      )}
                    >
                      <div className="flex items-center gap-2">
                        {task.status === "completed" && (
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                        )}
                        {task.status === "uploading" && (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-500 flex-shrink-0" />
                        )}
                        {task.status === "error" && (
                          <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                        )}
                        {task.status === "waiting" && (
                          <div className="h-4 w-4 rounded-full border-2 border-muted-foreground flex-shrink-0" />
                        )}

                        <div className="flex-1 min-w-0">
                          <div
                            className="text-sm font-medium truncate"
                            title={task.file.name}
                          >
                            {task.file.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatFileSize(task.file.size)}
                          </div>
                        </div>

                        <div className="flex gap-1">
                          {task.status === "error" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onRetry(task.id)}
                              className="h-7 px-2 text-xs"
                            >
                              {t("fileTableModal.retry")}
                            </Button>
                          )}
                          {(task.status === "waiting" ||
                            task.status === "uploading") && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onCancel(task.id)}
                              className="h-7 w-7 p-0"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {task.status === "uploading" && (
                        <div className="space-y-1">
                          <Progress value={task.progress} className="h-1" />
                          <div className="text-xs text-muted-foreground text-right">
                            {task.progress}%
                          </div>
                        </div>
                      )}

                      {task.error && (
                        <div
                          className="text-xs text-red-500"
                          title={task.error}
                        >
                          {t("common.error")}: {task.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {folders.length === 0 && tasks.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p className="text-sm">{t("fileTableModal.uploadingFiles")}</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </>
  );
}
