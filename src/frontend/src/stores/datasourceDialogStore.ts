import { create } from "zustand";

interface DataSourceDialogStore {
  isOpen: boolean;
  openDialog: () => void;
  closeDialog: () => void;
}

const useDatasourceDialogStore = create<DataSourceDialogStore>((set) => ({
  isOpen: false,
  openDialog: () => set({ isOpen: true }),
  closeDialog: () => set({ isOpen: false }),
}));

export default useDatasourceDialogStore;
