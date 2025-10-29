import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import IconComponent from "@/components/common/genericIconComponent";
import ExecutionLogsComponent from "@/components/core/executionLogsComponent";
import useFlowsManagerStore from "@/stores/flowsManagerStore";
import BaseModal from "../baseModal";

export default function FlowLogsModal({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element {
  const { t } = useTranslation();
  const currentFlowId = useFlowsManagerStore((state) => state.currentFlowId);
  const [open, setOpen] = useState(false);
  const [searchParams] = useSearchParams();
  const flowIdFromUrl = searchParams.get("id");

  const flowId = currentFlowId ?? flowIdFromUrl;

  return (
    <BaseModal open={open} setOpen={setOpen} size="x-large">
      <BaseModal.Trigger asChild>{children}</BaseModal.Trigger>
      <BaseModal.Header description={t("flow.panel.logs.description")}>
        <div className="flex w-full justify-between">
          <div className="flex h-fit items-center">
            <span className="pr-2">{t("flow.panel.logs.displayName")}</span>
            <IconComponent name="ScrollText" className="mr-2 h-4 w-4" />
          </div>
          <div className="flex h-fit items-center">
            <span className="text-sm text-muted-foreground">
              Flow ID: {flowId?.slice(0, 8)}...
            </span>
          </div>
        </div>
      </BaseModal.Header>
      <BaseModal.Content>
        {flowId ? (
          <ExecutionLogsComponent flowId={flowId} />
        ) : (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <div className="text-center">
              <IconComponent
                name="AlertCircle"
                className="h-12 w-12 mx-auto mb-4 opacity-50"
              />
              <div>无法获取流程ID</div>
              <div className="text-sm mt-2">请确保在流程页面中打开此日志</div>
            </div>
          </div>
        )}
      </BaseModal.Content>
    </BaseModal>
  );
}
