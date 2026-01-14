// 最近访问项目管理工具函数
// Utility functions for managing recently visited folders

/**
 * 获取最近访问的项目 ID 列表
 * Get the list of recently visited folder IDs
 * @param limit - 返回的最大数量 / Maximum number to return (default: 5)
 * @returns Array of folder IDs sorted by recency
 */
export function getRecentFolders(limit: number = 5): string[] {
  const recent = localStorage.getItem("recentFolders");
  if (!recent) return [];

  try {
    const parsed = JSON.parse(recent);
    return Array.isArray(parsed) ? parsed.slice(0, limit) : [];
  } catch (error) {
    console.error("Error parsing recentFolders from localStorage:", error);
    return [];
  }
}

/**
 * 记录项目访问，更新最近访问列表
 * Track folder visit and update recent folders list
 * @param folderId - The folder ID to track
 */
export function trackFolderVisit(folderId: string): void {
  if (!folderId) return;

  const recent = getRecentFolders(10); // Get top 10 to maintain history

  // 将当前访问的项目移到最前面，移除重复项
  // Move current folder to front, remove duplicates
  const updated = [folderId, ...recent.filter((id) => id !== folderId)].slice(
    0,
    10,
  ); // Keep maximum 10 in history

  localStorage.setItem("recentFolders", JSON.stringify(updated));
}

/**
 * 清除最近访问记录
 * Clear all recent folders history
 */
export function clearRecentFolders(): void {
  localStorage.removeItem("recentFolders");
}

/**
 * 检查项目是否在最近访问列表中
 * Check if a folder is in the recent list
 * @param folderId - The folder ID to check
 * @returns true if folder is in recent list
 */
export function isRecentFolder(folderId: string): boolean {
  const recent = getRecentFolders(10);
  return recent.includes(folderId);
}
