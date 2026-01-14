// Connector API Type Definitions
// Based on backend schemas from src/backend/base/langflow/api/v1/connectors.py

export enum ConnectorType {
  SLACK = "SLACK",
  NOTION = "NOTION",
  GITHUB = "GITHUB",
  LINEAR = "LINEAR",
  JIRA = "JIRA",
  CONFLUENCE = "CONFLUENCE",
  BOOKSTACK = "BOOKSTACK",
  AIRTABLE = "AIRTABLE",
  LUMA = "LUMA",
  GOOGLE_CALENDAR = "GOOGLE_CALENDAR",
  GMAIL = "GMAIL",
  ZOOM = "ZOOM",
  WEB_CRAWLER = "WEB_CRAWLER",
}

export interface ConnectorRead {
  id: number;
  name: string;
  connector_type: ConnectorType;
  search_space_id: number;
  config: Record<string, any>;
  last_indexed_at: string | null;
  is_periodic: boolean;
  created_at: string;
  updated_at: string;
  status?: "active" | "inactive" | "error";
}

export interface ConnectorCreate {
  name: string;
  connector_type: ConnectorType;
  search_space_id: number;
  config: Record<string, any>;
  is_periodic?: boolean;
}

export interface ConnectorUpdate {
  name?: string;
  config?: Record<string, any>;
  is_periodic?: boolean;
}

export interface GetConnectorsParams {
  search_space_id: number;
}

export interface IndexConnectorParams {
  start_date?: string | null;
  end_date?: string | null;
}

export interface IndexConnectorResponse {
  message: string;
  documents_created: number;
}

export interface DeleteConnectorResponse {
  message: string;
}

export interface GitHubRepository {
  name: string;
  full_name: string;
  private: boolean;
  html_url: string;
  description: string | null;
}

export interface GetGitHubRepositoriesParams {
  access_token: string;
}

export interface GetGitHubRepositoriesResponse {
  repositories: GitHubRepository[];
}
