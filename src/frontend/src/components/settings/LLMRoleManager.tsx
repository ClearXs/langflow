import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useGetGlobalLLMConfigsQuery,
  useGetLLMConfigsQuery,
} from "@/controllers/API/queries/llm-configs";
import {
  useGetLLMPreferences,
  usePutUpdateLLMPreferences,
} from "@/controllers/API/queries/llm-preferences";
import type {
  GlobalLLMConfigRead,
  LLMConfigRead,
} from "@/types/api/llm-configs";

interface LLMRoleManagerProps {
  spaceId: number;
}

type CombinedConfig = (LLMConfigRead | GlobalLLMConfigRead) & {
  is_global?: boolean;
};

export default function LLMRoleManager({ spaceId }: LLMRoleManagerProps) {
  const { t } = useTranslation();

  // State for role assignments
  const [agentLLMId, setAgentLLMId] = useState<number | null>(null);
  const [documentSummaryLLMId, setDocumentSummaryLLMId] = useState<
    number | null
  >(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch global configs
  const { data: globalConfigs = [], isLoading: isLoadingGlobal } =
    useGetGlobalLLMConfigsQuery();

  // Fetch custom configs for this space
  const { data: customConfigs = [], isLoading: isLoadingCustom } =
    useGetLLMConfigsQuery({}, { searchSpaceId: spaceId });

  // Fetch current LLM preferences
  const {
    data: preferences,
    isLoading: isLoadingPreferences,
    refetch: refetchPreferences,
  } = useGetLLMPreferences({ spaceId });

  // Update mutation
  const { mutateAsync: updatePreferences, isPending: isUpdating } =
    usePutUpdateLLMPreferences();

  // Combine global and custom configs
  const allConfigs: CombinedConfig[] = [
    ...globalConfigs.map((config) => ({ ...config, is_global: true })),
    ...customConfigs,
  ];

  // Initialize state from preferences
  useEffect(() => {
    if (preferences) {
      setAgentLLMId(preferences.agent_llm_id ?? null);
      setDocumentSummaryLLMId(preferences.document_summary_llm_id ?? null);
    }
  }, [preferences]);

  // Detect changes
  useEffect(() => {
    if (!preferences) return;

    const changed =
      agentLLMId !== (preferences.agent_llm_id ?? null) ||
      documentSummaryLLMId !== (preferences.document_summary_llm_id ?? null);

    setHasChanges(changed);
  }, [agentLLMId, documentSummaryLLMId, preferences]);

  const handleSave = async () => {
    try {
      await updatePreferences({
        spaceId,
        data: {
          agent_llm_id: agentLLMId,
          document_summary_llm_id: documentSummaryLLMId,
        },
      });

      toast.success(t("spaces.settings.llmRoles.saveSuccess"));
      refetchPreferences();
      setHasChanges(false);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.detail ||
        error?.message ||
        t("spaces.settings.llmRoles.saveError");
      toast.error(errorMessage);
    }
  };

  const handleReset = () => {
    if (preferences) {
      setAgentLLMId(preferences.agent_llm_id ?? null);
      setDocumentSummaryLLMId(preferences.document_summary_llm_id ?? null);
      setHasChanges(false);
    }
  };

  const getConfigLabel = (config: CombinedConfig) => {
    const globalBadge = config.is_global ? " (Global)" : "";
    return `${config.name} - ${config.provider}/${config.model_name}${globalBadge}`;
  };

  const isLoading = isLoadingGlobal || isLoadingCustom || isLoadingPreferences;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-sm text-muted-foreground">
          {t("common.loading")}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">
          {t("spaces.settings.llmRoles.title")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("spaces.settings.llmRoles.description")}
        </p>
      </div>

      {/* Role Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Agent LLM */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t("spaces.settings.llmRoles.agentLLM")}
            </CardTitle>
            <CardDescription>
              {t("spaces.settings.llmRoles.agentLLMDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="agent_llm">
                {t("spaces.settings.llmRoles.selectModel")}
              </Label>
              <Select
                value={agentLLMId?.toString() || ""}
                onValueChange={(value) =>
                  setAgentLLMId(value ? Number(value) : null)
                }
              >
                <SelectTrigger id="agent_llm">
                  <SelectValue
                    placeholder={t(
                      "spaces.settings.llmRoles.selectPlaceholder",
                    )}
                  />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {allConfigs.map((config) => (
                    <SelectItem key={config.id} value={config.id.toString()}>
                      {getConfigLabel(config)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Document Summary LLM */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t("spaces.settings.llmRoles.documentSummaryLLM")}
            </CardTitle>
            <CardDescription>
              {t("spaces.settings.llmRoles.documentSummaryLLMDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="document_summary_llm">
                {t("spaces.settings.llmRoles.selectModel")}
              </Label>
              <Select
                value={documentSummaryLLMId?.toString() || ""}
                onValueChange={(value) =>
                  setDocumentSummaryLLMId(value ? Number(value) : null)
                }
              >
                <SelectTrigger id="document_summary_llm">
                  <SelectValue
                    placeholder={t(
                      "spaces.settings.llmRoles.selectPlaceholder",
                    )}
                  />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {allConfigs.map((config) => (
                    <SelectItem key={config.id} value={config.id.toString()}>
                      {getConfigLabel(config)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      {hasChanges && (
        <div className="flex items-center gap-3 pt-4 border-t">
          <Button onClick={handleSave} disabled={isUpdating}>
            {isUpdating
              ? t("common.saving")
              : t("spaces.settings.llmRoles.saveChanges")}
          </Button>
          <Button variant="outline" onClick={handleReset} disabled={isUpdating}>
            {t("common.cancel")}
          </Button>
        </div>
      )}

      {/* Info Message */}
      {allConfigs.length === 0 && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {t("spaces.settings.llmRoles.noConfigsAvailable")}
          </p>
        </div>
      )}
    </div>
  );
}
