// LLM Configs API Type Definitions

export interface GlobalLLMConfigRead {
  id: number;
  name: string;
  description?: string;
  provider: string;
  custom_provider: string | null;
  model_name: string;
  api_base: string | null;
  litellm_params: Record<string, any>;
  system_instructions: string | null;
  use_default_system_instructions: boolean;
  citations_enabled: boolean;
  is_global: boolean;
}

export interface LLMConfigRead {
  id: number;
  search_space_id: number;
  name: string;
  provider: string;
  model_name: string;
  api_base: string | null;
  api_key: string | null;
  config: Record<string, any>;
  custom_provider: string | null;
  system_instructions: string | null;
  use_default_system_instructions: boolean;
  citations_enabled: boolean;
  litellm_params: Record<string, any>;
  created_at: string;
  updated_at: string | null;
}

export interface LLMConfigCreate {
  search_space_id: number;
  name: string;
  provider: string;
  model_name: string;
  api_base?: string | null;
  api_key?: string | null;
  config?: Record<string, any> | null;
  custom_provider?: string | null;
  system_instructions?: string | null;
  use_default_system_instructions?: boolean | null;
  citations_enabled?: boolean | null;
  litellm_params?: Record<string, any> | null;
}

export interface LLMConfigUpdate {
  name?: string | null;
  provider?: string | null;
  model_name?: string | null;
  api_base?: string | null;
  api_key?: string | null;
  config?: Record<string, any> | null;
  custom_provider?: string | null;
  system_instructions?: string | null;
  use_default_system_instructions?: boolean | null;
  citations_enabled?: boolean | null;
  litellm_params?: Record<string, any> | null;
}

export interface DeleteLLMConfigResponse {
  message: string;
}

export interface DefaultSystemInstructionsResponse {
  instructions: string;
}
