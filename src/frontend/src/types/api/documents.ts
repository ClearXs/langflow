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
  connector_id: number | null;
  space_id: number;
  user_id: string;
  title: string;
  content: string;
  url: string | null;
  doc_type: string;
  blocknote_document: any | null;
  embedding: number[] | null;
  content_hash: string;
  unique_identifier_hash: string | null;
  content_needs_reindexing: boolean;
  document_metadata: any | null;
  file_name: string | null;
  file_type: string | null;
  file_size: number | null;
  data_construction_file_id: number | null;
  data_construction_folder_id: number | null;
  etl_service: string | null;
  chunk_count: number;
  token_count: number;
  processing_status: string;
  processing_error: string | null;
  graph_extracted: boolean;
  entity_count: number;
  relation_count: number;
  created_at: string;
  updated_at: string | null;
  indexed_at: string | null;
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
  total_pages: number;
}

export interface GetDocumentsParams {
  search_space_id: number;
  document_types?: DocumentType[];
  page?: number;
  page_size?: number;
}

export interface SearchDocumentsParams {
  search_space_id: number;
  title: string;
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
