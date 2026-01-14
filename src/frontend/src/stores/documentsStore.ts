import { create } from "zustand";
import type { DocumentsStoreType } from "@/types/zustand/documents";

const useDocumentsStore = create<DocumentsStoreType>((set, get) => ({
  // State
  selectedDocumentIds: [],
  documentFilters: {},
  isLoading: false,

  // Actions
  selectDocument: (id) =>
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.includes(id)
        ? state.selectedDocumentIds
        : [...state.selectedDocumentIds, id],
    })),

  deselectDocument: (id) =>
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.filter(
        (docId) => docId !== id,
      ),
    })),

  toggleDocumentSelection: (id) =>
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.includes(id)
        ? state.selectedDocumentIds.filter((docId) => docId !== id)
        : [...state.selectedDocumentIds, id],
    })),

  clearSelection: () => set({ selectedDocumentIds: [] }),

  selectMultiple: (ids) => set({ selectedDocumentIds: ids }),

  setFilters: (filters) =>
    set((state) => ({
      documentFilters: { ...state.documentFilters, ...filters },
    })),

  resetFilters: () => set({ documentFilters: {} }),

  setIsLoading: (isLoading) => set({ isLoading }),

  // Computed getters
  getSelectedCount: () => get().selectedDocumentIds.length,

  isSelected: (id) => get().selectedDocumentIds.includes(id),
}));

export default useDocumentsStore;
