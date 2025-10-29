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
          ? t("modal.saveChanges.title.flow")
          : truncate(flowName, { length: 32 })) +
        " " +
        t("modal.saveChanges.title.unsavedChanges")
      }
      cancelText={
        autoSave ? undefined : t("modal.saveChanges.buttons.exitAnyway")
      }
      confirmationText={
        autoSave ? undefined : t("modal.saveChanges.buttons.saveAndExit")
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
            {t("modal.saveChanges.messages.saving")}
          </div>
        ) : (
          <>
            <div className="mb-4 flex w-full items-center gap-3 rounded-md bg-yellow-100 px-4 py-2 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-100">
              <ForwardedIconComponent name="Info" className="h-5 w-5" />
              {t("modal.saveChanges.messages.lastSaved", {
                time: lastSaved ?? t("modal.saveChanges.messages.never"),
              })}
            </div>
            {t("modal.saveChanges.messages.warningLost")}{" "}
            <a
              target="_blank"
              className="text-secondary underline"
              href="https://docs.langflow.org/configuration-auto-save"
              rel="noopener"
            >
              {t("modal.saveChanges.links.enableAutoSave")}
            </a>{" "}
            {t("modal.saveChanges.messages.avoidLosing")}
          </>
        )}
      </ConfirmationModal.Content>
    </ConfirmationModal>
  );
}
