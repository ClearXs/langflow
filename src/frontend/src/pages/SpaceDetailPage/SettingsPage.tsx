import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import LLMRoleManager from "@/components/settings/LLMRoleManager";
import ModelConfigManager from "@/components/settings/ModelConfigManager";
import SystemInstructionsEditor from "@/components/settings/SystemInstructionsEditor";
import GraphSettings from "@/components/settings/GraphSettings";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SettingsPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [activeTab, setActiveTab] = useState("model-configs");

  return (
    <div className="flex flex-col h-full">
      {/* Settings Header */}
      <div className="border-b px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">
            {t("spaces.settings.title")}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t("spaces.settings.manageSpaceSettings")}
          </p>
        </div>
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-auto">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="h-full flex flex-col"
        >
          <div className="border-b px-6">
            <TabsList className="h-12">
              <TabsTrigger value="model-configs" className="gap-2">
                {t("spaces.settings.modelConfigs")}
              </TabsTrigger>
              <TabsTrigger value="role-assignments" className="gap-2">
                {t("spaces.settings.roleAssignments")}
              </TabsTrigger>
              <TabsTrigger value="system-instructions" className="gap-2">
                {t("spaces.settings.systemInstructions")}
              </TabsTrigger>
              <TabsTrigger value="knowledge-graph" className="gap-2">
                {t("spaces.settings.knowledgeGraph")}
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-auto">
            <TabsContent value="model-configs" className="h-full m-0 p-6">
              <ModelConfigManager spaceId={Number(spaceId)} />
            </TabsContent>

            <TabsContent value="role-assignments" className="h-full m-0 p-6">
              <LLMRoleManager spaceId={Number(spaceId)} />
            </TabsContent>

            <TabsContent value="system-instructions" className="h-full m-0 p-6">
              <SystemInstructionsEditor spaceId={Number(spaceId)} />
            </TabsContent>

            <TabsContent value="knowledge-graph" className="h-full m-0 p-6">
              <GraphSettings spaceId={Number(spaceId)} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
