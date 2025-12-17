import { Panel } from "@xyflow/react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import ExecutionHistoryButton from "@/components/core/executionHistoryButton";
import { Button } from "@/components/ui/button";
import FlowLogsModal from "@/modals/flowLogsModal";

const LogCanvasControls = () => {
  const { t } = useTranslation();

  return (
    <Panel
      data-testid="canvas_controls"
      className="!m-2"
      position="bottom-left"
    >
      <div className="flex flex-row gap-2">
        <FlowLogsModal>
          <Button
            variant="primary"
            size="sm"
            className="flex items-center !gap-1.5"
          >
            <ForwardedIconComponent name="Terminal" className="text-primary" />
            <span className="text-mmd font-normal">
              {t("components.logCanvasControls.logs")}
            </span>
          </Button>
        </FlowLogsModal>
        <ExecutionHistoryButton />
      </div>
    </Panel>
  );
};

export default LogCanvasControls;
