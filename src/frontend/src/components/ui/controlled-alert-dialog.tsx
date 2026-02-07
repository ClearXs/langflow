import { useEffect } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./alert-dialog";

interface ControlledAlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  cancelText: string;
  confirmText: string;
  onConfirm: () => void | Promise<void>;
  isLoading?: boolean;
  confirmClassName?: string;
  children?: React.ReactNode;
}

/**
 * A controlled AlertDialog wrapper that ensures proper cleanup of overlays.
 *
 * This component addresses the issue where Radix UI's AlertDialog overlay
 * may not be properly cleaned up when closed, leaving an invisible barrier
 * that blocks all interactions with the page.
 */
export function ControlledAlertDialog({
  open,
  onOpenChange,
  title,
  description,
  cancelText,
  confirmText,
  onConfirm,
  isLoading = false,
  confirmClassName,
  children,
}: ControlledAlertDialogProps) {
  // Force cleanup of any stale overlays when component unmounts
  useEffect(() => {
    return () => {
      // Clean up any Radix UI portal overlays that might be stuck
      const cleanupOverlays = () => {
        const overlays = document.querySelectorAll('[data-radix-dialog-overlay]');
        overlays.forEach(overlay => {
          if (overlay.parentElement) {
            overlay.parentElement.removeChild(overlay);
          }
        });

        // Also clean up any portal containers that might be empty
        const portals = document.querySelectorAll('[data-radix-portal]');
        portals.forEach(portal => {
          if (!portal.hasChildNodes()) {
            if (portal.parentElement) {
              portal.parentElement.removeChild(portal);
            }
          }
        });
      };

      // Use setTimeout to ensure this runs after React's cleanup
      setTimeout(cleanupOverlays, 100);
    };
  }, []);

  // Additional cleanup when dialog closes
  useEffect(() => {
    if (!open) {
      // Give Radix time to finish its close animation
      const timer = setTimeout(() => {
        const overlays = document.querySelectorAll('[data-radix-dialog-overlay][data-state="closed"]');
        overlays.forEach(overlay => {
          if (overlay.parentElement) {
            overlay.parentElement.removeChild(overlay);
          }
        });
      }, 300); // Wait for animation to complete

      return () => clearTimeout(timer);
    }
  }, [open]);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        {children || (
          <>
            <AlertDialogHeader>
              <AlertDialogTitle>{title}</AlertDialogTitle>
              <AlertDialogDescription>{description}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isLoading}>
                {cancelText}
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={onConfirm}
                disabled={isLoading}
                className={confirmClassName}
              >
                {confirmText}
              </AlertDialogAction>
            </AlertDialogFooter>
          </>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
