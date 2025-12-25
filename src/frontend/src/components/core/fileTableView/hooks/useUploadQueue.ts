/**
 * useUploadQueue Hook
 *
 * Manages file upload queue with concurrency control:
 * - Upload max N files concurrently (default: 5)
 * - Track progress for each file
 * - Support pause/resume/cancel/retry
 * - Handle errors gracefully
 */

import { useCallback, useRef, useState } from "react";
import type { UseFileManagementReturn } from "@/controllers/DATA_API/useFileManagement";
import type { FileToUpload } from "./useFolderUpload";

// ==================== Types ====================

export interface UploadTask {
  id: string;
  file: File;
  folderId: number | string;
  status: "waiting" | "uploading" | "completed" | "error";
  progress: number; // 0-100
  error?: string;
  abortController?: AbortController;
}

export interface UploadQueueState {
  tasks: UploadTask[];
  activeUploads: number;
  maxConcurrent: number;
  totalCompleted: number;
  totalFailed: number;
  isRunning: boolean;
}

// ==================== Hook ====================

export interface UseUploadQueueReturn {
  state: UploadQueueState;
  enqueueFiles: (files: FileToUpload[]) => void;
  startQueue: () => void;
  pauseQueue: () => void;
  cancelTask: (taskId: string) => void;
  retryTask: (taskId: string) => void;
  clearCompleted: () => void;
  reset: () => void;
}

export function useUploadQueue(
  maxConcurrent: number = 5,
  fileOps: UseFileManagementReturn,
): UseUploadQueueReturn {
  const [state, setState] = useState<UploadQueueState>({
    tasks: [],
    activeUploads: 0,
    maxConcurrent,
    totalCompleted: 0,
    totalFailed: 0,
    isRunning: false,
  });

  const tasksRef = useRef<UploadTask[]>([]);
  const activeTasksRef = useRef<Set<string>>(new Set());
  const isRunningRef = useRef(false);

  /**
   * Process next task in queue
   * Maintains concurrency limit and starts new tasks as others complete
   */
  const processNext = useCallback(async () => {
    if (!isRunningRef.current) return;
    if (activeTasksRef.current.size >= maxConcurrent) return;

    const nextTask = tasksRef.current.find((t) => t.status === "waiting");
    if (!nextTask) {
      // No more waiting tasks, check if queue is complete
      if (activeTasksRef.current.size === 0) {
        isRunningRef.current = false;
        setState((prev) => ({ ...prev, isRunning: false }));
      }
      return;
    }

    // Start upload
    activeTasksRef.current.add(nextTask.id);
    nextTask.status = "uploading";

    setState((prev) => ({
      ...prev,
      activeUploads: activeTasksRef.current.size,
      tasks: [...prev.tasks],
    }));

    try {
      await fileOps.uploadFile(
        nextTask.folderId,
        nextTask.file,
        (progressEvent) => {
          const percent = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 1),
          );
          nextTask.progress = percent;
          setState((prev) => ({ ...prev, tasks: [...prev.tasks] }));
        },
        nextTask.abortController?.signal,
      );

      // Success
      nextTask.status = "completed";
      nextTask.progress = 100;
      setState((prev) => ({
        ...prev,
        totalCompleted: prev.totalCompleted + 1,
        tasks: [...prev.tasks],
      }));
    } catch (error: any) {
      // Check if it was cancelled
      if (error.name === "AbortError" || error.name === "CanceledError") {
        // Task was cancelled, remove it
        const taskIndex = tasksRef.current.findIndex(
          (t) => t.id === nextTask.id,
        );
        if (taskIndex !== -1) {
          tasksRef.current.splice(taskIndex, 1);
        }
        setState((prev) => ({
          ...prev,
          tasks: [...tasksRef.current],
        }));
      } else {
        // Upload error
        nextTask.status = "error";
        nextTask.error = error.message || String(error);
        setState((prev) => ({
          ...prev,
          totalFailed: prev.totalFailed + 1,
          tasks: [...prev.tasks],
        }));
      }
    } finally {
      activeTasksRef.current.delete(nextTask.id);
      setState((prev) => ({
        ...prev,
        activeUploads: activeTasksRef.current.size,
      }));

      // Process next task
      processNext();
    }
  }, [maxConcurrent, fileOps]);

  /**
   * Add files to queue
   */
  const enqueueFiles = useCallback((files: FileToUpload[]) => {
    const newTasks: UploadTask[] = files.map((f) => ({
      id: `${f.file.name}-${Date.now()}-${Math.random()}`,
      file: f.file,
      folderId: f.targetFolderId!,
      status: "waiting",
      progress: 0,
      abortController: new AbortController(),
    }));

    tasksRef.current.push(...newTasks);
    setState((prev) => ({
      ...prev,
      tasks: [...tasksRef.current],
    }));
  }, []);

  /**
   * Start queue processing
   */
  const startQueue = useCallback(() => {
    isRunningRef.current = true;
    setState((prev) => ({ ...prev, isRunning: true }));

    // Start multiple concurrent uploads
    for (let i = 0; i < maxConcurrent; i++) {
      processNext();
    }
  }, [maxConcurrent, processNext]);

  /**
   * Pause queue
   */
  const pauseQueue = useCallback(() => {
    isRunningRef.current = false;
    setState((prev) => ({ ...prev, isRunning: false }));
  }, []);

  /**
   * Cancel a specific task
   */
  const cancelTask = useCallback((taskId: string) => {
    const task = tasksRef.current.find((t) => t.id === taskId);
    if (task) {
      task.abortController?.abort();

      // If task is waiting, just remove it
      if (task.status === "waiting") {
        const taskIndex = tasksRef.current.findIndex((t) => t.id === taskId);
        if (taskIndex !== -1) {
          tasksRef.current.splice(taskIndex, 1);
          setState((prev) => ({ ...prev, tasks: [...tasksRef.current] }));
        }
      }
    }
  }, []);

  /**
   * Retry a failed task
   */
  const retryTask = useCallback(
    (taskId: string) => {
      const task = tasksRef.current.find((t) => t.id === taskId);
      if (task && task.status === "error") {
        task.status = "waiting";
        task.progress = 0;
        task.error = undefined;
        task.abortController = new AbortController();

        setState((prev) => ({
          ...prev,
          totalFailed: Math.max(0, prev.totalFailed - 1),
          tasks: [...tasksRef.current],
        }));

        // If queue is running, process next
        if (isRunningRef.current) {
          processNext();
        }
      }
    },
    [processNext],
  );

  /**
   * Clear completed tasks
   */
  const clearCompleted = useCallback(() => {
    tasksRef.current = tasksRef.current.filter((t) => t.status !== "completed");
    setState((prev) => ({
      ...prev,
      tasks: [...tasksRef.current],
      totalCompleted: 0,
    }));
  }, []);

  /**
   * Reset queue (clear all tasks)
   */
  const reset = useCallback(() => {
    // Cancel all active uploads
    tasksRef.current.forEach((task) => {
      task.abortController?.abort();
    });

    tasksRef.current = [];
    activeTasksRef.current.clear();
    isRunningRef.current = false;

    setState({
      tasks: [],
      activeUploads: 0,
      maxConcurrent,
      totalCompleted: 0,
      totalFailed: 0,
      isRunning: false,
    });
  }, [maxConcurrent]);

  return {
    state,
    enqueueFiles,
    startQueue,
    pauseQueue,
    cancelTask,
    retryTask,
    clearCompleted,
    reset,
  };
}
