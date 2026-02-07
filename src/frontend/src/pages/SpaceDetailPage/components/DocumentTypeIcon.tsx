import {
  File,
  FileCode,
  FileSpreadsheet,
  FileText,
  FileType,
  Globe,
  Presentation,
  Video,
} from "lucide-react";
import type { DocumentTypeEnum } from "./types";

/**
 * Get icon component for document type
 */
export function getDocumentTypeIcon(type: DocumentTypeEnum) {
  const iconMap: Record<DocumentTypeEnum, typeof FileText> = {
    txt: FileText,
    pdf: FileType,
    web: Globe,
    youtube: Video,
    markdown: FileCode,
    docx: FileText,
    xlsx: FileSpreadsheet,
    pptx: Presentation,
    csv: FileSpreadsheet,
    json: FileCode,
    xml: FileCode,
    html: FileCode,
  };

  return iconMap[type] || File;
}

/**
 * Document type chip component
 */
interface DocumentTypeChipProps {
  type: DocumentTypeEnum;
  className?: string;
}

export function DocumentTypeChip({
  type,
  className = "",
}: DocumentTypeChipProps) {
  const Icon = getDocumentTypeIcon(type);

  const colorMap: Record<DocumentTypeEnum, string> = {
    txt: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    pdf: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    web: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    youtube: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    markdown:
      "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    docx: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    xlsx: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    pptx: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    csv: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    json: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    xml: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
    html: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  };

  const colorClass =
    colorMap[type] ||
    "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${colorClass} ${className}`}
    >
      <Icon className="h-3 w-3" />
      <span className="uppercase">{type}</span>
    </div>
  );
}
