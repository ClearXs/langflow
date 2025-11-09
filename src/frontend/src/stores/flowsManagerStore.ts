import { cloneDeep, debounce } from "lodash";
import { create } from "zustand";
import { SAVE_DEBOUNCE_TIME } from "@/constants/constants";
import type { FlowType } from "../types/flow";
import type {
  FlowsManagerStoreType,
  UseUndoRedoOptions,
} from "../types/zustand/flowsManager";
import useFlowStore from "./flowStore";

const defaultOptions: UseUndoRedoOptions = {
  maxHistorySize: 100,
  enableShortcuts: true,
};

const past = {};
const future = {};

// Fast hash function for quick state comparison
const fastHash = (nodes: any[], edges: any[]) => {
  return `${nodes.length}-${edges.length}-${nodes.map(n => n.id).join(',')}-${edges.map(e => e.id).join(',')}`;
};

// Store last hash to avoid redundant snapshots
const lastSnapshotHash: Record<string, string> = {};

const useFlowsManagerStore = create<FlowsManagerStoreType>((set, get) => ({
  IOModalOpen: false,
  setIOModalOpen: (IOModalOpen: boolean) => {
    set({ IOModalOpen });
  },
  healthCheckMaxRetries: 5,
  setHealthCheckMaxRetries: (healthCheckMaxRetries: number) =>
    set({ healthCheckMaxRetries }),
  autoSaving: true,
  setAutoSaving: (autoSaving: boolean) => set({ autoSaving }),
  autoSavingInterval: SAVE_DEBOUNCE_TIME,
  setAutoSavingInterval: (autoSavingInterval: number) =>
    set({ autoSavingInterval }),
  examples: [],
  setExamples: (examples: FlowType[]) => {
    set({ examples });
  },
  currentFlowId: "",
  setCurrentFlow: (flow: FlowType | undefined) => {
    set({
      currentFlow: flow,
      currentFlowId: flow?.id ?? "",
    });
    useFlowStore.getState().resetFlow(flow);
  },
  getFlowById: (id: string) => {
    return get().flows?.find((flow) => flow.id === id);
  },
  flows: undefined,
  setFlows: (flows: FlowType[]) => {
    set({
      flows,
      currentFlow: flows.find((flow) => flow.id === get().currentFlowId),
    });
  },
  currentFlow: undefined,
  saveLoading: false,
  setSaveLoading: (saveLoading: boolean) => set({ saveLoading }),
  isLoading: false,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
  takeSnapshot: () => {
    const currentFlowId = get().currentFlowId;
    // push the current graph to the past state
    const flowStore = useFlowStore.getState();

    // Fast hash-based early exit - avoid expensive cloneDeep if state hasn't changed
    const currentHash = fastHash(flowStore.nodes, flowStore.edges);
    if (lastSnapshotHash[currentFlowId] === currentHash) {
      return; // Skip snapshot if state is identical
    }

    const newState = {
      nodes: cloneDeep(flowStore.nodes),
      edges: cloneDeep(flowStore.edges),
    };
    const pastLength = past[currentFlowId]?.length ?? 0;

    // Deep comparison only if hash is different but we have history
    if (pastLength > 0) {
      // Use faster comparison - check node/edge counts first
      const lastState = past[currentFlowId][pastLength - 1];
      if (
        lastState.nodes.length === newState.nodes.length &&
        lastState.edges.length === newState.edges.length &&
        JSON.stringify(lastState) === JSON.stringify(newState)
      ) {
        return;
      }
    }

    if (pastLength > 0) {
      past[currentFlowId] = past[currentFlowId].slice(
        pastLength - defaultOptions.maxHistorySize + 1,
        pastLength,
      );

      past[currentFlowId].push(newState);
    } else {
      past[currentFlowId] = [newState];
    }

    // Update the hash after successful snapshot
    lastSnapshotHash[currentFlowId] = currentHash;
    future[currentFlowId] = [];
  },
  undo: () => {
    const newState = useFlowStore.getState();
    const currentFlowId = get().currentFlowId;
    const pastLength = past[currentFlowId]?.length ?? 0;
    const pastState = past[currentFlowId]?.[pastLength - 1] ?? null;

    if (pastState) {
      past[currentFlowId] = past[currentFlowId].slice(0, pastLength - 1);

      if (!future[currentFlowId]) future[currentFlowId] = [];
      future[currentFlowId].push({
        nodes: newState.nodes,
        edges: newState.edges,
      });

      newState.setNodes(pastState.nodes);
      newState.setEdges(pastState.edges);
    }
  },
  redo: () => {
    const newState = useFlowStore.getState();
    const currentFlowId = get().currentFlowId;
    const futureLength = future[currentFlowId]?.length ?? 0;
    const futureState = future[currentFlowId]?.[futureLength - 1] ?? null;

    if (futureState) {
      future[currentFlowId] = future[currentFlowId].slice(0, futureLength - 1);

      if (!past[currentFlowId]) past[currentFlowId] = [];
      past[currentFlowId].push({
        nodes: newState.nodes,
        edges: newState.edges,
      });

      newState.setNodes(futureState.nodes);
      newState.setEdges(futureState.edges);
    }
  },
  searchFlowsComponents: "",
  setSearchFlowsComponents: (searchFlowsComponents: string) => {
    set({ searchFlowsComponents });
  },
  selectedFlowsComponentsCards: [],
  setSelectedFlowsComponentsCards: (selectedFlowsComponentsCards: string[]) => {
    set({ selectedFlowsComponentsCards });
  },
  resetStore: () => {
    set({
      flows: [],
      currentFlow: undefined,
      currentFlowId: "",
      searchFlowsComponents: "",
      selectedFlowsComponentsCards: [],
    });
  },
}));

export default useFlowsManagerStore;
