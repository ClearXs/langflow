/**
 * Connector utility functions and types
 */

export interface ConnectorConfig {
  [key: string]: string;
}

export interface Connector {
  id: number;
  name: string;
  connector_type: string;
  config: ConnectorConfig;
  created_at: string;
  user_id: string;
}

export interface CreateConnectorRequest {
  name: string;
  connector_type: string;
  config: ConnectorConfig;
}

/**
 * Get connector type display name
 */
export const getConnectorTypeDisplay = (type: string): string => {
  const typeMap: Record<string, string> = {
    TAVILY_API: "Tavily API",
    SEARXNG_API: "SearxNG",
    SLACK: "Slack",
    NOTION: "Notion",
    GITHUB: "GitHub",
    LINEAR: "Linear",
    JIRA: "Jira",
    CONFLUENCE: "Confluence",
    BOOKSTACK: "BookStack",
    AIRTABLE: "Airtable",
    LUMA: "Luma",
    GOOGLE_CALENDAR: "Google Calendar",
    GMAIL: "Gmail",
    ZOOM: "Zoom",
    WEB_CRAWLER: "Web Crawler",
  };
  return typeMap[type] || type;
};

/**
 * Get connector type icon
 */
export const getConnectorTypeIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    SLACK: "slack",
    NOTION: "notion",
    GITHUB: "github",
    LINEAR: "linear",
    JIRA: "jira",
    CONFLUENCE: "confluence",
    BOOKSTACK: "bookstack",
    AIRTABLE: "airtable",
    LUMA: "luma",
    GOOGLE_CALENDAR: "google-calendar",
    GMAIL: "gmail",
    ZOOM: "zoom",
    WEB_CRAWLER: "web-crawler",
  };
  return iconMap[type] || "plug";
};
