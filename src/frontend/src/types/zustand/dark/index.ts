export type DarkStoreType = {
  dark: boolean;
  stars: number;
  version: string;
  latestVersion: string;
  discordCount: number;
  setDark: (dark: boolean) => void;
  refreshVersion: (v: string) => void;
  refreshLatestVersion: (v: string) => void;
  refreshStars: () => void;
  refreshDiscordCount: () => void;
};
