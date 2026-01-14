// LLM Configs API Type Definitions

export interface GlobalLLMConfigRead {
  id: number;
  name: string;
  provider: string;
  model: string;
  temperature: number;
}

export interface LLMConfigRead {
  id: number;
  name: string;
  provider: string;
  model: string;
  api_key: string | null;
  api_base: string | null;
  temperature: number;
  max_tokens: number | null;
  system_instructions: string | null;
  enable_citations: boolean;
  search_space_id: number;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigCreate {
  name: string;
  provider: string;
  model: string;
  api_key?: string | null;
  api_base?: string | null;
  temperature?: number;
  max_tokens?: number | null;
  system_instructions?: string | null;
  enable_citations?: boolean;
  search_space_id: number;
}

export interface LLMConfigUpdate {
  name?: string;
  provider?: string;
  model?: string;
  api_key?: string | null;
  api_base?: string | null;
  temperature?: number;
  max_tokens?: number | null;
  system_instructions?: string | null;
  enable_citations?: boolean;
}

export interface DeleteLLMConfigResponse {
  message: string;
}

export interface DefaultSystemInstructionsResponse {
  default_system_instructions: string;
}
