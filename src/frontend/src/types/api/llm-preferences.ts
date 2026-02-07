// LLM Preferences API Type Definitions

export interface LLMPreferencesRead {
  agent_llm_id: number | null;
  document_summary_llm_id: number | null;
}

export interface LLMPreferencesUpdate {
  agent_llm_id?: number | null;
  document_summary_llm_id?: number | null;
}
