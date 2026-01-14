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

export interface Connector {
  id: number;
  name: string;
  connector_type: ConnectorType;
  search_space_id: number;
  config: Record<string, any>;
  last_indexed_at?: string;
  is_periodic: boolean;
  created_at: string;
  updated_at: string;
  status?: "active" | "inactive" | "error";
}

export interface ConnectorConfig {
  [key: string]: any;
}

export interface ConnectorsStoreType {
  // State
  activeConnectorId: number | null;
  connectors: Connector[];
  connectorConfig: ConnectorConfig;
  isLoading: boolean;
  isSyncing: boolean;

  // Actions
  setActiveConnectorId: (id: number | null) => void;
  setConnectors: (connectors: Connector[]) => void;
  updateConnectorConfig: (config: Partial<ConnectorConfig>) => void;
  resetConnectorConfig: () => void;
  setIsLoading: (isLoading: boolean) => void;
  setIsSyncing: (isSyncing: boolean) => void;

  // Computed getters
  getActiveConnector: () => Connector | null;
  getConnectorsByType: (type: ConnectorType) => Connector[];
}
