import { formatDistanceToNow } from "date-fns";
import {
  Calendar,
  Download,
  File,
  FileText,
  MoreVertical,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  useDeleteDocument,
  useGetDocumentsQuery,
  usePostUploadDocuments,
} from "@/controllers/API/queries/documents";

export default function DocumentsPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const {
    data: documents = [],
    isLoading,
    refetch,
  } = useGetDocumentsQuery(
    { search_space_id: Number(spaceId) },
    { enabled: !!spaceId },
  );

  const { mutateAsync: uploadDocuments, isPending: isUploading } =
    usePostUploadDocuments();
  const { mutateAsync: deleteDocument, isPending: isDeleting } =
    useDeleteDocument();

  const filteredDocuments = documents.filter((doc) =>
    doc.title?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFiles(event.target.files);
    }
  };

  const handleUploadDocuments = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      toast.error(t("spaces.documents.selectFiles"));
      return;
    }

    try {
      await uploadDocuments({
        files: Array.from(selectedFiles),
        search_space_id: Number(spaceId),
      });
      toast.success(
        t("spaces.documents.uploadSuccess", { count: selectedFiles.length }),
      );
      setSelectedFiles(null);
      setIsUploadDialogOpen(false);
      refetch();
    } catch (error) {
      toast.error(t("spaces.documents.uploadError"));
    }
  };

  const handleDeleteDocument = async (documentId: number) => {
    try {
      await deleteDocument({ id: documentId });
      toast.success(t("spaces.documents.deleteSuccess"));
      refetch();
    } catch (error) {
      toast.error(t("spaces.documents.deleteError"));
    }
  };

  const getDocumentIcon = (type: string) => {
    if (type.includes("pdf")) return "📄";
    if (type.includes("image")) return "🖼️";
    if (type.includes("text")) return "📝";
    if (type.includes("word") || type.includes("doc")) return "📘";
    if (type.includes("excel") || type.includes("spreadsheet")) return "📊";
    return "📎";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Documents Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">
              {t("spaces.documents.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("spaces.documents.subtitle")}
            </p>
          </div>
          <Button onClick={() => setIsUploadDialogOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            {t("spaces.documents.uploadDocument")}
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("spaces.documents.searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Documents Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-5 bg-muted rounded w-3/4" />
                </CardHeader>
                <CardContent>
                  <div className="h-16 bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!isLoading && filteredDocuments.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <Card className="max-w-md border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <FileText className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  {searchQuery
                    ? t("spaces.documents.noDocumentsFound")
                    : t("spaces.documents.noDocumentsYet")}
                </h3>
                <p className="text-muted-foreground text-center max-w-sm mb-6">
                  {searchQuery
                    ? t("spaces.documents.tryAdjusting")
                    : t("spaces.documents.uploadFirstDocument")}
                </p>
                {!searchQuery && (
                  <Button onClick={() => setIsUploadDialogOpen(true)}>
                    <Upload className="mr-2 h-4 w-4" />
                    {t("spaces.documents.uploadYourFirstDocument")}
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {!isLoading && filteredDocuments.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocuments.map((doc) => (
              <Card key={doc.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <span className="text-2xl">
                        {getDocumentIcon(doc.document_type)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold line-clamp-2">
                          {doc.title}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          {doc.document_type}
                        </p>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t("spaces.documents.delete")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>

                <CardFooter className="text-xs text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-3 w-3" />
                  {t("spaces.documents.uploaded")}{" "}
                  {formatDistanceToNow(new Date(doc.created_at), {
                    addSuffix: true,
                  })}
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Upload Documents Dialog */}
      <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("spaces.documents.uploadDialogTitle")}</DialogTitle>
            <DialogDescription>
              {t("spaces.documents.uploadDialogDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
                accept=".pdf,.txt,.doc,.docx,.md,.csv,.json"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center"
              >
                <File className="h-12 w-12 text-muted-foreground mb-3" />
                <p className="text-sm font-medium mb-1">
                  {t("spaces.documents.clickToSelect")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("spaces.documents.fileTypes")}
                </p>
              </label>
            </div>

            {selectedFiles && selectedFiles.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium mb-2">
                  {t("spaces.documents.selectedFiles", {
                    count: selectedFiles.length,
                  })}
                </p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {Array.from(selectedFiles).map((file, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <File className="h-3 w-3" />
                      {file.name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsUploadDialogOpen(false);
                setSelectedFiles(null);
              }}
              disabled={isUploading}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleUploadDocuments}
              disabled={isUploading || !selectedFiles}
            >
              {isUploading
                ? t("spaces.documents.uploading")
                : t("spaces.documents.upload")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
