import { useState } from "react";
import { useTranslation } from "react-i18next";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { usePostMessageContext } from "@/contexts/postMessageContext";
import useSaveFlow from "@/hooks/flows/use-save-flow";
import { SaveChangesModal } from "@/modals/saveChangesModal";
import useFlowsManagerStore from "@/stores/flowsManagerStore";

export default function BackButton() {
  const { t } = useTranslation();
  const postMessageContext = usePostMessageContext();
  const [showSaveModal, setShowSaveModal] = useState(false);
  const saveFlow = useSaveFlow();
  const currentSavedFlow = useFlowsManagerStore((state) => state.currentFlow);

  const handleSaveAndBack = () => {
    setShowSaveModal(true);

    // Start saving immediately (async)
    saveFlow()
      .then(() => {
        // Save succeeded
      })
      .catch(() => {
        // Save failed, but still proceed
      })
      .finally(() => {
        // Close regardless of success or failure
        postMessageContext.sendToParent("close");
      });
  };

  const updatedAt = currentSavedFlow?.updated_at;

  return (
    <>
      <Button
        variant="ghost"
        size="md"
        className="!px-2.5 font-normal"
        data-testid="publish-button"
        onClick={handleSaveAndBack}
      >
        <IconComponent name="SquareArrowLeft" className="!h-5 !w-5" />
        {t("flow.saveAndBack")}
      </Button>

      {showSaveModal && currentSavedFlow && (
        <SaveChangesModal
          onSave={() => {}}
          onCancel={() => setShowSaveModal(false)}
          onProceed={() => {}}
          flowName={currentSavedFlow.name}
          lastSaved={
            updatedAt
              ? new Date(updatedAt).toLocaleString("en-US", {
                  hour: "numeric",
                  minute: "numeric",
                  month: "numeric",
                  day: "numeric",
                })
              : undefined
          }
          autoSave={true}
        />
      )}
    </>
  );
}
