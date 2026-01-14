import { useCallback, useState } from "react";
import {
  useDeleteConnector,
  useGetConnectorQuery,
  usePostCreateConnector,
  usePostIndexConnector,
  usePutUpdateConnector,
} from "@/controllers/API/queries/connectors";
import useAlertStore from "@/stores/alertStore";
import type { ConnectorRead, ConnectorType } from "@/types/api";

export interface UseConnectorEditPageProps {
  connectorId?: number;
  searchSpaceId: number;
}

export function useConnectorEditPage({
  connectorId,
  searchSpaceId,
}: UseConnectorEditPageProps) {
  const [isIndexing, setIsIndexing] = useState(false);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  // Fetch connector data if editing
  const {
    data: connector,
    isLoading,
    refetch,
  } = useGetConnectorQuery(
    {
      enabled: !!connectorId,
    },
    { connectorId: connectorId! },
  );

  // Create connector mutation
  const createConnectorMutation = usePostCreateConnector({
    onSuccess: (data) => {
      setSuccessData({
        title: "Connector created successfully",
      });
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to create connector",
        list: [error.message],
      });
    },
  });

  // Update connector mutation
  const updateConnectorMutation = usePutUpdateConnector({
    onSuccess: (data) => {
      setSuccessData({
        title: "Connector updated successfully",
      });
      refetch();
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to update connector",
        list: [error.message],
      });
    },
  });

  // Delete connector mutation
  const deleteConnectorMutation = useDeleteConnector({
    onSuccess: () => {
      setSuccessData({
        title: "Connector deleted successfully",
      });
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to delete connector",
        list: [error.message],
      });
    },
  });

  // Index connector mutation
  const indexConnectorMutation = usePostIndexConnector({
    onSuccess: (data) => {
      setSuccessData({
        title: "Indexing started",
        list: [`${data.documents_created} documents will be created`],
      });
      setIsIndexing(false);
      refetch();
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to start indexing",
        list: [error.message],
      });
      setIsIndexing(false);
    },
  });

  const handleCreateConnector = useCallback(
    async (data: {
      name: string;
      connector_type: ConnectorType;
      config: Record<string, any>;
      is_periodic?: boolean;
    }) => {
      await createConnectorMutation.mutateAsync({
        data: {
          ...data,
          search_space_id: searchSpaceId,
        },
      });
    },
    [createConnectorMutation, searchSpaceId],
  );

  const handleUpdateConnector = useCallback(
    async (data: {
      name?: string;
      config?: Record<string, any>;
      is_periodic?: boolean;
    }) => {
      if (!connectorId) return;
      await updateConnectorMutation.mutateAsync({
        connectorId,
        data,
      });
    },
    [updateConnectorMutation, connectorId],
  );

  const handleDeleteConnector = useCallback(async () => {
    if (!connectorId) return;
    await deleteConnectorMutation.mutateAsync({
      connectorId,
      search_space_id: searchSpaceId,
    });
  }, [deleteConnectorMutation, connectorId, searchSpaceId]);

  const handleIndexConnector = useCallback(
    async (params?: {
      start_date?: string | null;
      end_date?: string | null;
    }) => {
      if (!connectorId) return;
      setIsIndexing(true);
      await indexConnectorMutation.mutateAsync({
        connectorId,
        search_space_id: searchSpaceId,
        params,
      });
    },
    [indexConnectorMutation, connectorId, searchSpaceId],
  );

  return {
    connector,
    isLoading,
    isIndexing,
    createConnector: handleCreateConnector,
    updateConnector: handleUpdateConnector,
    deleteConnector: handleDeleteConnector,
    indexConnector: handleIndexConnector,
    isCreating: createConnectorMutation.isPending,
    isUpdating: updateConnectorMutation.isPending,
    isDeleting: deleteConnectorMutation.isPending,
  };
}
