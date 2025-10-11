import { useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import BaseModal from "../../../../modals/baseModal";
import SwitchOutputView from "./components/switchOutputView";
import { useTranslation } from "react-i18next";

export default function OutputModal({
  nodeId,
  outputName,
  children,
  disabled,
  open,
  setOpen,
}): JSX.Element {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"Outputs" | "Logs">("Outputs");
  
  return (
    <BaseModal
      open={open}
      setOpen={setOpen}
      disable={disabled}
      size="large"
      className="z-50"
    >
      <BaseModal.Header description={t("components.output.description")}>
        <div
          className="flex items-center"
          data-testid={`${nodeId}-${outputName}-output-modal`}
        >
          <span className="pr-2">{t("components.output.title")}</span>
        </div>
      </BaseModal.Header>
      <BaseModal.Content>
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as "Outputs" | "Logs")}
          className={
            "absolute top-6 flex flex-col self-center overflow-hidden rounded-md border bg-muted text-center"
          }
        >
          <TabsList>
            <TabsTrigger value="Outputs">{t("components.output.tabs.outputs")}</TabsTrigger>
            <TabsTrigger value="Logs">{t("components.output.tabs.logs")}</TabsTrigger>
          </TabsList>
        </Tabs>
        <SwitchOutputView
          nodeId={nodeId}
          outputName={outputName}
          type={activeTab}
        />
      </BaseModal.Content>
      <BaseModal.Footer close></BaseModal.Footer>
      <BaseModal.Trigger asChild>{children}</BaseModal.Trigger>
    </BaseModal>
  );
}