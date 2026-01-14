export interface Space {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  is_shared?: boolean;
  member_count?: number;
  document_count?: number;
}

export interface QueryParams {
  page: number;
  page_size: number;
  search: string;
  sort_by: string;
  sort_order: "asc" | "desc";
}

export interface SpacesStoreType {
  // State
  activeSpaceId: number | null;
  spaces: Space[];
  queryParams: QueryParams;
  isLoading: boolean;

  // Actions
  setActiveSpaceId: (id: number | null) => void;
  setSpaces: (spaces: Space[]) => void;
  setQueryParams: (params: Partial<QueryParams>) => void;
  setIsLoading: (isLoading: boolean) => void;
  resetSpaces: () => void;

  // Computed getters
  getActiveSpace: () => Space | null;
}
