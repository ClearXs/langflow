import { Download, Eye, Loader2, MoreHorizontal, Trash2 } from "lucide-react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDownloadDocument } from "@/controllers/API/queries/documents";
import type { Document } from "./types";

interface RowActionsProps {
  document: Document;
  onDelete: () => Promise<boolean>;
}

export function RowActions({ document, onDelete }: RowActionsProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Download mutation
  const downloadDocument = useDownloadDocument();

  const handleView = () => {
    // Navigate to document viewer/editor
    navigate(`/spaces/${document.space_id}/documents/${document.id}`);
  };

  const handleDownload = async () => {
    await downloadDocument.mutateAsync(document.id);
  };

  const handleDeleteClick = () => {
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    try {
      const success = await onDelete();
      if (success) {
        setShowDeleteDialog(false);
      }
    } finally {
      setIsDeleting(false);
    }
  };

  // Force cleanup of overlays and body styles when dialog closes
  useEffect(() => {
    if (!showDeleteDialog) {
      // Cleanup function
      const cleanup = () => {
        // Remove stuck overlays
        const overlays = window.document.querySelectorAll('[data-radix-dialog-overlay]');
        overlays.forEach((overlay) => {
          overlay.parentElement?.removeChild(overlay);
        });

        // Remove pointer-events: none from body
        window.document.body.style.removeProperty('pointer-events');

        // Also check for any radix portal containers
        const portals = window.document.querySelectorAll('[data-radix-portal]');
        portals.forEach((portal) => {
          if (!portal.hasChildNodes()) {
            portal.parentElement?.removeChild(portal);
          }
        });
      };

      // Clean immediately
      cleanup();

      // Clean again after animation completes
      const timer = setTimeout(cleanup, 500);

      return () => clearTimeout(timer);
    }
  }, [showDeleteDialog]);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <MoreHorizontal className="h-4 w-4" />
            <span className="sr-only">{t("common.openMenu")}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleView}>
            <Eye className="mr-2 h-4 w-4" />
            {t("documents.actions.view")}
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={handleDownload}
            disabled={downloadDocument.isPending}
          >
            {downloadDocument.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {t("documents.actions.download")}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleDeleteClick}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t("documents.actions.delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog
        key={`delete-document-${document.id}`}
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("documents.delete.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("documents.delete.description", { title: document.title })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t("documents.delete.deleting")}
                </>
              ) : (
                t("documents.delete.confirm")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
