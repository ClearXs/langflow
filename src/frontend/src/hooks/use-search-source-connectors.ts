import { useCallback, useState } from "react";

export interface SearchSourceConnector {
  id: number;
  name: string;
  connector_type: string;
  is_indexable: boolean;
  last_indexed_at: string | null;
  config: Record<string, any>;
  search_space_id: number;
  user_id?: string;
  created_at?: string;
  periodic_indexing_enabled: boolean;
  indexing_frequency_minutes: number | null;
  next_scheduled_at: string | null;
}

export interface ConnectorSourceItem {
  id: number;
  name: string;
  type: string;
  sources: any[];
}

/**
 * Hook to manage search source connectors
 * This is a placeholder - actual implementation should use API hooks when available
 */
export const useSearchSourceConnectors = (
  lazy: boolean = false,
  searchSpaceId?: number,
) => {
  const [connectors, setConnectors] = useState<SearchSourceConnector[]>([]);
  const [isLoading, setIsLoading] = useState(!lazy);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [connectorSourceItems, setConnectorSourceItems] = useState<
    ConnectorSourceItem[]
  >([
    {
      id: 1,
      name: "Crawled URL",
      type: "CRAWLED_URL",
      sources: [],
    },
    {
      id: 2,
      name: "File",
      type: "FILE",
      sources: [],
    },
    {
      id: 3,
      name: "Extension",
      type: "EXTENSION",
      sources: [],
    },
    {
      id: 4,
      name: "Youtube Video",
      type: "YOUTUBE_VIDEO",
      sources: [],
    },
  ]);

  const fetchConnectors = useCallback(async (spaceId?: number) => {
    // TODO: Implement actual API call when search-source-connectors endpoint is created
    setIsLoading(false);
    setIsLoaded(true);
    return [];
  }, []);

  const refetch = useCallback(() => {
    return fetchConnectors(searchSpaceId);
  }, [fetchConnectors, searchSpaceId]);

  return {
    connectors,
    isLoading,
    error,
    refetch,
    fetchConnectors,
    connectorSourceItems,
  };
};
