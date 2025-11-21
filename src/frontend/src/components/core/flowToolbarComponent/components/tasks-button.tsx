import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import TasksModal from "@/modals/tasksModal";
import useFlowStore from "@/stores/flowStore";

const TasksButton = () => {
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
      <ShadTooltip side="bottom" content={t("tasks.viewTooltip")}>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClick}
          disabled={!currentFlowId}
          className="h-11 gap-2 px-3"
          data-testid="tasks-btn"
        >
          <ForwardedIconComponent
            name="ListChecks"
            className="h-4 w-4"
            strokeWidth={1.5}
          />
          <span className="hidden md:block">{t("tasks.title")}</span>
        </Button>
      </ShadTooltip>

      {currentFlowId && (
        <TasksModal open={open} setOpen={setOpen} flowId={currentFlowId} />
      )}
    </>
  );
};

export default TasksButton;
