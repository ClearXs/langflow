/**
 * Document types supported by the system
 */
export type DocumentTypeEnum =
  | "txt"
  | "pdf"
  | "web"
  | "youtube"
  | "markdown"
  | "docx"
  | "xlsx"
  | "pptx"
  | "csv"
  | "json"
  | "xml"
  | "html";

/**
 * Document interface matching backend DocumentRead model
 */
export interface Document {
  id: number;
  title: string;
  doc_type: DocumentTypeEnum; // Changed from document_type to match backend field name
  content?: string;
  created_at: string;
  updated_at?: string;
  space_id: number;
  user_id: string;
  data_construction_file_id?: number;
  data_construction_folder_id?: number;
  processing_status?: string;
  error_message?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Column visibility state for table
 */
export interface ColumnVisibility {
  title: boolean;
  doc_type: boolean; // Changed from document_type
  content: boolean;
  created_at: boolean;
}

/**
 * Sort key type for table sorting
 */
export type SortKey = keyof Pick<Document, "title" | "doc_type" | "created_at">;
