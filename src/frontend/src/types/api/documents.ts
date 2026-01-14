// Document API Type Definitions
// Based on backend schemas from src/backend/base/langflow/api/v1/documents.py

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

export interface DocumentRead {
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

export interface DocumentCreate {
  title: string;
  document_type: DocumentType;
  content: string;
  search_space_id: number;
  url?: string | null;
}

export interface DocumentUpdate {
  title?: string;
  content?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface GetDocumentsParams {
  search_space_id: number;
  document_types?: DocumentType[];
  page?: number;
  page_size?: number;
}

export interface SearchDocumentsParams {
  search_space_id: number;
  title_query: string;
  page?: number;
  page_size?: number;
}

export interface DocumentTypeCount {
  document_type: DocumentType;
  count: number;
}

export interface GetDocumentTypeCountsParams {
  search_space_id: number;
}

export interface FileUploadResponse {
  message: string;
  document_ids: number[];
  failed_files?: string[];
}

export interface DeleteDocumentResponse {
  message: string;
}
