import { FolderUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

interface FileUploadButtonProps {
  onClick: () => void;
  hasActiveUploads?: boolean;
}

const FileUploadButton = ({
  onClick,
  hasActiveUploads = false,
}: FileUploadButtonProps) => {
  const { t } = useTranslation();

  return (
    <Button
      variant="ghost"
      data-testid="canvas_file_upload_button"
      className="group rounded-none px-2 py-2 hover:bg-muted"
      unstyled
      title={t("fileTableModal.uploadProgress")}
      onClick={onClick}
    >
      <div className="relative">
        <FolderUp
          aria-hidden="true"
          className="text-muted-foreground group-hover:text-primary !h-5 !w-5"
        />
        {hasActiveUploads && (
          <div className="absolute -top-1 -right-1 h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
        )}
      </div>
    </Button>
  );
};

export default FileUploadButton;
