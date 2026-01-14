import { create } from "zustand";

export type ResearchMode = "QNA" | "RESEARCH" | "DEEP_RESEARCH";

export interface ChatDocument {
  id: number;
  title: string;
  document_type: string;
}

export interface ChatStoreType {
  // State
  currentChatId: string | null;
  isLoading: boolean;
  researchMode: ResearchMode;
  selectedConnectors: string[];
  selectedDocuments: ChatDocument[];
  topK: number;

  // Actions
  setCurrentChatId: (id: string | null) => void;
  setIsLoading: (isLoading: boolean) => void;
  setResearchMode: (mode: ResearchMode) => void;
  setSelectedConnectors: (connectors: string[]) => void;
  addSelectedConnector: (connector: string) => void;
  removeSelectedConnector: (connector: string) => void;
  setSelectedDocuments: (documents: ChatDocument[]) => void;
  addSelectedDocument: (document: ChatDocument) => void;
  removeSelectedDocument: (documentId: number) => void;
  setTopK: (topK: number) => void;
  resetChat: () => void;
}

const useChatStore = create<ChatStoreType>((set, get) => ({
  // State
  currentChatId: null,
  isLoading: false,
  researchMode: "QNA",
  selectedConnectors: [],
  selectedDocuments: [],
  topK: 5,

  // Actions
  setCurrentChatId: (id) => set({ currentChatId: id }),

  setIsLoading: (isLoading) => set({ isLoading }),

  setResearchMode: (mode) => set({ researchMode: mode }),

  setSelectedConnectors: (connectors) =>
    set({ selectedConnectors: connectors }),

  addSelectedConnector: (connector) =>
    set((state) => ({
      selectedConnectors: [...state.selectedConnectors, connector],
    })),

  removeSelectedConnector: (connector) =>
    set((state) => ({
      selectedConnectors: state.selectedConnectors.filter(
        (c) => c !== connector,
      ),
    })),

  setSelectedDocuments: (documents) => set({ selectedDocuments: documents }),

  addSelectedDocument: (document) =>
    set((state) => ({
      selectedDocuments: [...state.selectedDocuments, document],
    })),

  removeSelectedDocument: (documentId) =>
    set((state) => ({
      selectedDocuments: state.selectedDocuments.filter(
        (d) => d.id !== documentId,
      ),
    })),

  setTopK: (topK) => set({ topK }),

  resetChat: () =>
    set({
      currentChatId: null,
      isLoading: false,
      researchMode: "QNA",
      selectedConnectors: [],
      selectedDocuments: [],
      topK: 5,
    }),
}));

export default useChatStore;
