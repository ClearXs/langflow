import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import LineageModal from "@/modals/lineageModal";
import useFlowStore from "@/stores/flowStore";

const LineageButton = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const currentFlowId = useFlowStore((state) => state.currentFlow?.id);

  const handleClick = () => {
    if (currentFlowId) {
      setOpen(true);
    }
  };

  return (
    <>
      <ShadTooltip side="bottom" content={t("lineage.analyzeTooltip")}>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClick}
          disabled={!currentFlowId}
          className="h-11 gap-2 px-3"
          data-testid="lineage-btn"
        >
          <ForwardedIconComponent
            name="GitBranch"
            className="h-4 w-4"
            strokeWidth={1.5}
          />
          <span className="hidden md:block">{t("lineage.analyze")}</span>
        </Button>
      </ShadTooltip>

      {currentFlowId && (
        <LineageModal open={open} setOpen={setOpen} flowId={currentFlowId} />
      )}
    </>
  );
};

export default LineageButton;
