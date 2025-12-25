/**
 * Export utilities for execution history data
 */

/**
 * Export data as JSON file
 */
export function exportAsJSON(data: any, filename: string = "execution-data") {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  downloadBlob(blob, `${filename}.json`);
}

/**
 * Export table data as CSV file
 */
export function exportAsCSV(
  columns: any[],
  rows: any[],
  filename: string = "execution-data",
) {
  if (!columns || !rows || rows.length === 0) {
    return;
  }

  // Create CSV header from column definitions
  const headers = columns.map((col) => col.headerName || col.field).join(",");

  // Create CSV rows
  const csvRows = rows.map((row) => {
    return columns
      .map((col) => {
        const value = row[col.field];
        // Handle values that might contain commas or quotes
        if (typeof value === "string") {
          return `"${value.replace(/"/g, '""')}"`;
        }
        if (typeof value === "object") {
          return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
        }
        return value ?? "";
      })
      .join(",");
  });

  const csvContent = [headers, ...csvRows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  downloadBlob(blob, `${filename}.csv`);
}

/**
 * Download blob as file
 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Copy data to clipboard as JSON
 */
export async function copyToClipboard(data: any): Promise<boolean> {
  try {
    const jsonString = JSON.stringify(data, null, 2);

    // 尝试使用现代 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(jsonString);
      return true;
    }

    // 回退方案：使用传统的 execCommand 方法
    const textArea = document.createElement("textarea");
    textArea.value = jsonString;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);
      return successful;
    } catch (err) {
      document.body.removeChild(textArea);
      console.error("Fallback copy failed:", err);
      return false;
    }
  } catch (error) {
    console.error("Failed to copy to clipboard:", error);
    return false;
  }
}
