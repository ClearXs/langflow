import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AnnouncementStore {
  announcementDismissed: boolean;
  setAnnouncementDismissed: (dismissed: boolean) => void;
}

export const useAnnouncementStore = create<AnnouncementStore>()(
  persist(
    (set) => ({
      announcementDismissed: false,
      setAnnouncementDismissed: (dismissed) =>
        set({ announcementDismissed: dismissed }),
    }),
    {
      name: "surfsense_announcement_dismissed",
    },
  ),
);
