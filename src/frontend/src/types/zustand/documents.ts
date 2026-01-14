export enum DocumentType {
  EXTENSION = "EXTENSION",
  CRAWLED_URL = "CRAWLED_URL",
  FILE = "FILE",
  SLACK_CONNECTOR = "SLACK_CONNECTOR",
  NOTION_CONNECTOR = "NOTION_CONNECTOR",
  GITHUB_CONNECTOR = "GITHUB_CONNECTOR",
  LINEAR_CONNECTOR = "LINEAR_CONNECTOR",
  JIRA_CONNECTOR = "JIRA_CONNECTOR",
  CONFLUENCE_CONNECTOR = "CONFLUENCE_CONNECTOR",
  BOOKSTACK_CONNECTOR = "BOOKSTACK_CONNECTOR",
  AIRTABLE_CONNECTOR = "AIRTABLE_CONNECTOR",
  LUMA_CONNECTOR = "LUMA_CONNECTOR",
  GOOGLE_CALENDAR_CONNECTOR = "GOOGLE_CALENDAR_CONNECTOR",
  GMAIL_CONNECTOR = "GMAIL_CONNECTOR",
  ZOOM_CONNECTOR = "ZOOM_CONNECTOR",
  YOUTUBE = "YOUTUBE",
}

export interface Document {
  id: number;
  title: string;
  document_type: DocumentType;
  content: string;
  search_space_id: number;
  created_at: string;
  updated_at: string;
  chunk_count?: number;
  total_tokens?: number;
  url?: string | null;
  connector_id?: number | null;
}

export interface DocumentFilters {
  document_types: DocumentType[];
  search_space_id: number | null;
  date_from?: string;
  date_to?: string;
}

export interface DocumentsStoreType {
  // State
  selectedDocumentIds: number[];
  documentFilters: DocumentFilters;
  isLoading: boolean;

  // Actions
  selectDocument: (id: number) => void;
  deselectDocument: (id: number) => void;
  clearSelection: () => void;
  toggleDocument: (id: number) => void;
  setFilters: (filters: Partial<DocumentFilters>) => void;
  resetFilters: () => void;
  setIsLoading: (isLoading: boolean) => void;

  // Computed getters
  getSelectedCount: () => number;
  isDocumentSelected: (id: number) => boolean;
}
