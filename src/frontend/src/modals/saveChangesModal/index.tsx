import { truncate } from "lodash";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import Loading from "@/components/ui/loading";
import ConfirmationModal from "../confirmationModal";

export function SaveChangesModal({
  onSave,
  onProceed,
  onCancel,
  flowName,
  lastSaved,
  autoSave,
}: {
  onSave: () => void;
  onProceed: () => void;
  onCancel: () => void;
  flowName: string;
  lastSaved: string | undefined;
  autoSave: boolean;
}): JSX.Element {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);

  return (
    <ConfirmationModal
      open={true}
      onClose={onCancel}
      destructiveCancel
      title={
        (autoSave
          ? t("modals.saveChanges.title.flow")
          : truncate(flowName, { length: 32 })) +
        " " +
        t("modals.saveChanges.title.unsavedChanges")
      }
      cancelText={
        autoSave ? undefined : t("modals.saveChanges.buttons.exitAnyway")
      }
      confirmationText={
        autoSave ? undefined : t("modals.saveChanges.buttons.saveAndExit")
      }
      onConfirm={
        autoSave
          ? undefined
          : () => {
              setSaving(true);
              onSave();
            }
      }
      onCancel={onProceed}
      loading={autoSave ? true : saving}
      size="x-small"
    >
      <ConfirmationModal.Content>
        {autoSave ? (
          <div className="mb-4 flex w-full items-center gap-3 rounded-md bg-muted px-4 py-2 text-muted-foreground">
            <Loading className="h-5 w-5" />
            {t("modals.saveChanges.messages.saving")}
          </div>
        ) : (
          <>
            <div className="mb-4 flex w-full items-center gap-3 rounded-md bg-yellow-100 px-4 py-2 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-100">
              <ForwardedIconComponent name="Info" className="h-5 w-5" />
              {t("modals.saveChanges.messages.lastSaved", {
                time: lastSaved ?? t("modals.saveChanges.messages.never"),
              })}
            </div>
            {t("modals.saveChanges.messages.warningLost")}{" "}
            <a
              target="_blank"
              className="text-secondary underline"
              href="https://docs.langflow.org/configuration-auto-save"
              rel="noopener"
            >
              {t("modals.saveChanges.links.enableAutoSave")}
            </a>{" "}
            {t("modals.saveChanges.messages.avoidLosing")}
          </>
        )}
      </ConfirmationModal.Content>
    </ConfirmationModal>
  );
}
