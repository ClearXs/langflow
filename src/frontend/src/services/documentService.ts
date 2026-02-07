import { api } from "@/controllers/API/api";

export interface Document {
  id: number;
  title: string;
  document_type: string;
  search_space_id: number;
  created_at: string;
  updated_at: string | null;
}

export interface PaginatedDocumentsResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

/**
 * Search/list documents in a space
 */
export async function listDocuments(
  spaceId: number,
  query?: string,
  page = 0,
  pageSize = 50,
): Promise<PaginatedDocumentsResponse> {
  const params = new URLSearchParams({
    search_space_id: spaceId.toString(),
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (query) {
    params.append("q", query);
  }

  const response = await api.get<PaginatedDocumentsResponse>(
    `/api/v1/documents?${params.toString()}`,
  );
  return response.data;
}

/**
 * Search documents with a query
 */
export async function searchDocuments(
  spaceId: number,
  query: string,
  limit = 10,
): Promise<Document[]> {
  const response = await listDocuments(spaceId, query, 0, limit);
  return response.items;
}
