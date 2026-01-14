import { create } from "zustand";
import type { SpacesStoreType } from "@/types/zustand/spaces";

const useSpacesStore = create<SpacesStoreType>((set, get) => ({
  // State
  activeSpaceId: null,
  spaces: [],
  queryParams: {
    page: 1,
    page_size: 10,
    search: "",
    sort_by: "updated_at",
    sort_order: "desc",
  },
  isLoading: false,

  // Actions
  setActiveSpaceId: (id) => set({ activeSpaceId: id }),

  setSpaces: (spaces) => set({ spaces }),

  setQueryParams: (params) =>
    set((state) => ({
      queryParams: { ...state.queryParams, ...params },
    })),

  setIsLoading: (isLoading) => set({ isLoading }),

  resetSpaces: () =>
    set({
      activeSpaceId: null,
      spaces: [],
      queryParams: {
        page: 1,
        page_size: 10,
        search: "",
        sort_by: "updated_at",
        sort_order: "desc",
      },
      isLoading: false,
    }),

  // Computed getters
  getActiveSpace: () => {
    const { activeSpaceId, spaces } = get();
    if (!activeSpaceId) return null;
    return spaces.find((space) => space.id === activeSpaceId) ?? null;
  },
}));

export default useSpacesStore;
