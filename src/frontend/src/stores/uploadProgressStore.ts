import { create } from "zustand";
import type { FolderNode } from "@/components/core/fileTableView/hooks/useFolderUpload";
import type { UploadTask } from "@/components/core/fileTableView/hooks/useUploadQueue";

interface UploadProgressState {
  // Drawer visibility
  isDrawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  toggleDrawer: () => void;

  // Upload data
  folders: FolderNode[];
  tasks: UploadTask[];
  activeUploads: number;
  totalCompleted: number;
  totalFailed: number;
  isRunning: boolean;

  // Actions
  setFolders: (folders: FolderNode[]) => void;
  setTasks: (tasks: UploadTask[]) => void;
  setActiveUploads: (count: number) => void;
  setTotalCompleted: (count: number) => void;
  setTotalFailed: (count: number) => void;
  setIsRunning: (running: boolean) => void;

  // Upload control methods (set by FileTableView)
  uploadControls: {
    pauseQueue?: () => void;
    startQueue?: () => void;
    cancelTask?: (taskId: string) => void;
    retryTask?: (taskId: string) => void;
    clearCompleted?: () => void;
  };
  setUploadControls: (controls: UploadProgressState["uploadControls"]) => void;

  // Reset
  reset: () => void;
}

export const useUploadProgressStore = create<UploadProgressState>((set) => ({
  // Initial state
  isDrawerOpen: false,
  folders: [],
  tasks: [],
  activeUploads: 0,
  totalCompleted: 0,
  totalFailed: 0,
  isRunning: false,
  uploadControls: {},

  // Drawer actions
  setDrawerOpen: (open) => set({ isDrawerOpen: open }),
  toggleDrawer: () => set((state) => ({ isDrawerOpen: !state.isDrawerOpen })),

  // Data actions
  setFolders: (folders) => set({ folders }),
  setTasks: (tasks) => set({ tasks }),
  setActiveUploads: (count) => set({ activeUploads: count }),
  setTotalCompleted: (count) => set({ totalCompleted: count }),
  setTotalFailed: (count) => set({ totalFailed: count }),
  setIsRunning: (running) => set({ isRunning: running }),

  // Upload control actions
  setUploadControls: (controls) => set({ uploadControls: controls }),

  // Reset
  reset: () =>
    set({
      folders: [],
      tasks: [],
      activeUploads: 0,
      totalCompleted: 0,
      totalFailed: 0,
      isRunning: false,
    }),
}));
