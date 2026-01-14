// Space API Type Definitions
// Based on backend schemas from src/backend/base/langflow/api/v1/spaces.py

export interface SpaceRead {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  user_id: number;
  is_shared: boolean;
}

export interface SpaceWithStats {
  space: SpaceRead;
  member_count: number;
  document_count: number;
  connector_count: number;
}

export interface SpaceCreate {
  name: string;
  description?: string | null;
}

export interface SpaceUpdate {
  name?: string;
  description?: string | null;
  is_shared?: boolean;
}

export interface LLMPreferencesRead {
  id: number;
  search_space_id: number;
  chat_llm_config_id: number | null;
  fast_llm_config_id: number | null;
  query_llm_config_id: number | null;
  rerank_llm_config_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface LLMPreferencesUpdate {
  chat_llm_config_id?: number | null;
  fast_llm_config_id?: number | null;
  query_llm_config_id?: number | null;
  rerank_llm_config_id?: number | null;
}

export interface DeleteSpaceResponse {
  message: string;
}
