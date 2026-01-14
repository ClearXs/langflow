export interface EditorContent {
  type: string;
  content?: any[];
  [key: string]: any;
}

export interface EditorStoreType {
  // State
  activeDocumentId: number | null;
  editorContent: EditorContent | null;
  isDirty: boolean;
  isSaving: boolean;
  lastSaved: string | null;
  pendingNavigation: string | null;

  // Actions
  setActiveDocument: (id: number | null) => void;
  updateContent: (content: EditorContent) => void;
  setIsDirty: (isDirty: boolean) => void;
  setIsSaving: (isSaving: boolean) => void;
  setLastSaved: (timestamp: string | null) => void;
  setPendingNavigation: (url: string | null) => void;
  markClean: () => void;
  resetEditor: () => void;
}
