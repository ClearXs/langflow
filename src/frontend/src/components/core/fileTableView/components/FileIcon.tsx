import {
  Archive,
  File,
  FileAudio,
  FileCode,
  FileImage,
  FileJson,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Folder,
} from "lucide-react";

interface FileIconProps {
  fileName: string;
  fileType?: "file" | "folder";
  size?: number;
  className?: string;
}

export function FileIcon({
  fileName,
  fileType,
  size = 20,
  className = "",
}: FileIconProps) {
  // Get file extension
  const getFileExtension = (): string => {
    return fileName.split(".").pop()?.toLowerCase() || "";
  };

  // Get icon based on file type and extension
  const getIcon = () => {
    const iconSize = size;
    const iconProps = {
      size: iconSize,
      className: `${className} flex-shrink-0`,
    };

    if (fileType === "folder") {
      return (
        <Folder
          {...iconProps}
          className={`${iconProps.className} text-blue-500`}
        />
      );
    }

    const extension = getFileExtension();

    // Document files
    if (["doc", "docx"].includes(extension)) {
      return (
        <FileText
          {...iconProps}
          className={`${iconProps.className} text-blue-600`}
        />
      );
    }

    // Spreadsheet files
    if (["xls", "xlsx", "csv"].includes(extension)) {
      return (
        <FileSpreadsheet
          {...iconProps}
          className={`${iconProps.className} text-green-600`}
        />
      );
    }

    // PDF files
    if (extension === "pdf") {
      return (
        <FileText
          {...iconProps}
          className={`${iconProps.className} text-red-600`}
        />
      );
    }

    // Image files
    if (
      ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"].includes(extension)
    ) {
      return (
        <FileImage
          {...iconProps}
          className={`${iconProps.className} text-purple-600`}
        />
      );
    }

    // Video files
    if (["mp4", "avi", "mov", "wmv", "flv", "mkv"].includes(extension)) {
      return (
        <FileVideo
          {...iconProps}
          className={`${iconProps.className} text-pink-600`}
        />
      );
    }

    // Audio files
    if (["mp3", "wav", "ogg", "flac", "aac"].includes(extension)) {
      return (
        <FileAudio
          {...iconProps}
          className={`${iconProps.className} text-orange-600`}
        />
      );
    }

    // Code files
    if (
      [
        "js",
        "ts",
        "jsx",
        "tsx",
        "py",
        "java",
        "c",
        "cpp",
        "cs",
        "html",
        "css",
        "scss",
        "php",
        "rb",
        "go",
        "rs",
      ].includes(extension)
    ) {
      return (
        <FileCode
          {...iconProps}
          className={`${iconProps.className} text-yellow-600`}
        />
      );
    }

    // JSON/XML/Config files
    if (
      ["json", "xml", "yaml", "yml", "toml", "ini", "conf"].includes(extension)
    ) {
      return (
        <FileJson
          {...iconProps}
          className={`${iconProps.className} text-cyan-600`}
        />
      );
    }

    // Markdown files
    if (["md", "markdown"].includes(extension)) {
      return (
        <FileText
          {...iconProps}
          className={`${iconProps.className} text-gray-600`}
        />
      );
    }

    // Archive files
    if (["zip", "rar", "7z", "tar", "gz", "bz2"].includes(extension)) {
      return (
        <Archive
          {...iconProps}
          className={`${iconProps.className} text-amber-600`}
        />
      );
    }

    // Text files
    if (extension === "txt") {
      return (
        <FileText
          {...iconProps}
          className={`${iconProps.className} text-gray-500`}
        />
      );
    }

    // Default file icon
    return (
      <File {...iconProps} className={`${iconProps.className} text-gray-400`} />
    );
  };

  return getIcon();
}
