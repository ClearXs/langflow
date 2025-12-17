import { History } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import useFlowStore from "@/stores/flowStore";
import { cn } from "@/utils/utils";

export default function ExecutionHistoryButton() {
  const { t } = useTranslation();
  const isOpen = useFlowStore((state) => state.isExecutionHistoryOpen);
  const setOpen = useFlowStore((state) => state.setExecutionHistoryOpen);
  const flowPool = useFlowStore((state) => state.flowPool);

  const executedCount = Object.keys(flowPool).length;

  return (
    <Button
      variant="primary"
      size="sm"
      className={cn("flex items-center !gap-1.5", isOpen && "bg-muted")}
      onClick={() => setOpen(!isOpen)}
      data-testid="execution-history-button"
    >
      <History className="h-4 w-4 text-primary" />
      <span className="text-mmd font-normal">
        {t("executionHistory.buttonLabel")}
      </span>
      {executedCount > 0 && (
        <span className="ml-1 text-xs opacity-70">({executedCount})</span>
      )}
    </Button>
  );
}
