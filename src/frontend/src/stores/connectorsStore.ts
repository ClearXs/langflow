import { create } from "zustand";
import type {
  ConnectorsStoreType,
  ConnectorType,
} from "@/types/zustand/connectors";

const useConnectorsStore = create<ConnectorsStoreType>((set, get) => ({
  // State
  activeConnectorId: null,
  connectors: [],
  connectorConfig: {},
  isLoading: false,
  isSyncing: false,

  // Actions
  setActiveConnectorId: (id) => set({ activeConnectorId: id }),

  setConnectors: (connectors) => set({ connectors }),

  updateConnectorConfig: (config) =>
    set((state) => ({
      connectorConfig: { ...state.connectorConfig, ...config },
    })),

  resetConnectorConfig: () => set({ connectorConfig: {} }),

  setIsLoading: (isLoading) => set({ isLoading }),

  setIsSyncing: (isSyncing) => set({ isSyncing }),

  // Computed getters
  getActiveConnector: () => {
    const { activeConnectorId, connectors } = get();
    if (!activeConnectorId) return null;
    return (
      connectors.find((connector) => connector.id === activeConnectorId) ?? null
    );
  },

  getConnectorsByType: (type: ConnectorType) => {
    const { connectors } = get();
    return connectors.filter((connector) => connector.connector_type === type);
  },
}));

export default useConnectorsStore;
