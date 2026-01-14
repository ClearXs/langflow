import { create } from "zustand";
import type { EditorStoreType } from "@/types/zustand/editor";

const useEditorStore = create<EditorStoreType>((set, get) => ({
  // State
  activeDocumentId: null,
  editorContent: null,
  isDirty: false,
  isSaving: false,
  lastSaved: null,
  pendingNavigation: null,

  // Actions
  setActiveDocument: (id) =>
    set({
      activeDocumentId: id,
      editorContent: null,
      isDirty: false,
    }),

  updateContent: (content) =>
    set({
      editorContent: content,
      isDirty: true,
    }),

  setIsDirty: (isDirty) => set({ isDirty }),

  setIsSaving: (isSaving) => set({ isSaving }),

  setLastSaved: (timestamp) =>
    set({
      lastSaved: timestamp,
      isDirty: false,
    }),

  setPendingNavigation: (url) => set({ pendingNavigation: url }),

  markClean: () =>
    set({
      isDirty: false,
      lastSaved: new Date().toISOString(),
    }),

  resetEditor: () =>
    set({
      activeDocumentId: null,
      editorContent: null,
      isDirty: false,
      isSaving: false,
      lastSaved: null,
      pendingNavigation: null,
    }),
}));

export default useEditorStore;
