// utils/recentSpaces.ts

/**
 * Get recent space IDs from localStorage
 */
export function getRecentSpaces(limit: number = 5): string[] {
  const recent = localStorage.getItem("recentSpaces");
  if (!recent) return [];

  try {
    const parsed = JSON.parse(recent);
    return Array.isArray(parsed) ? parsed.slice(0, limit) : [];
  } catch {
    return [];
  }
}

/**
 * Track a space visit by adding it to recent spaces
 */
export function trackSpaceVisit(spaceId: string): void {
  const recent = getRecentSpaces(10);
  const updated = [spaceId, ...recent.filter((id) => id !== spaceId)].slice(
    0,
    10,
  ); // Keep last 10

  localStorage.setItem("recentSpaces", JSON.stringify(updated));
}

/**
 * Clear all recent spaces from localStorage
 */
export function clearRecentSpaces(): void {
  localStorage.removeItem("recentSpaces");
}
