import { useEffect, useMemo, useState } from "react";
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
import { Switch } from "@/components/ui/switch";
import {
  useGetGlobalLLMConfigsQuery,
  useGetLLMConfigsQuery,
} from "@/controllers/API/queries/llm-configs";
import {
  useGetSpaceQuery,
  usePutUpdateSpace,
} from "@/controllers/API/queries/spaces";
import type {
  GlobalLLMConfigRead,
  LLMConfigRead,
} from "@/types/api/llm-configs";

interface GraphSettingsProps {
  spaceId: number;
}

type CombinedConfig = (LLMConfigRead | GlobalLLMConfigRead) & {
  is_global?: boolean;
};

export default function GraphSettings({ spaceId }: GraphSettingsProps) {
  const { t } = useTranslation();
  const { data: space, isLoading: isLoadingSpace } = useGetSpaceQuery(
    {},
    { spaceId },
  );
  const { mutateAsync: updateSpace, isPending: isUpdating } =
    usePutUpdateSpace();

  const { data: globalConfigs = [], isLoading: isLoadingGlobal } =
    useGetGlobalLLMConfigsQuery();
  const { data: customConfigs = [], isLoading: isLoadingCustom } =
    useGetLLMConfigsQuery({}, { searchSpaceId: spaceId });

  const [enableKnowledgeGraph, setEnableKnowledgeGraph] = useState(false);
  const [autoEntityExtraction, setAutoEntityExtraction] = useState(true);
  const [graphLlmId, setGraphLlmId] = useState<number | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const allConfigs: CombinedConfig[] = useMemo(
    () => [
      ...globalConfigs.map((config) => ({ ...config, is_global: true })),
      ...customConfigs,
    ],
    [globalConfigs, customConfigs],
  );

  useEffect(() => {
    if (!space) return;
    setEnableKnowledgeGraph(space.enable_knowledge_graph);
    setAutoEntityExtraction(space.auto_entity_extraction);
    setGraphLlmId(space.graph_llm_id ?? null);
  }, [space]);

  useEffect(() => {
    if (!space) return;
    const changed =
      enableKnowledgeGraph !== space.enable_knowledge_graph ||
      autoEntityExtraction !== space.auto_entity_extraction ||
      graphLlmId !== (space.graph_llm_id ?? null);
    setHasChanges(changed);
  }, [space, enableKnowledgeGraph, autoEntityExtraction, graphLlmId]);

  const handleSave = async () => {
    try {
      await updateSpace({
        spaceId,
        data: {
          enable_knowledge_graph: enableKnowledgeGraph,
          auto_entity_extraction: autoEntityExtraction,
          graph_llm_id: graphLlmId,
        },
      });
      toast.success(t("spaces.settings.graph.saveSuccess"));
      setHasChanges(false);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.detail ||
        error?.message ||
        t("spaces.settings.graph.saveError");
      toast.error(errorMessage);
    }
  };

  const handleReset = () => {
    if (!space) return;
    setEnableKnowledgeGraph(space.enable_knowledge_graph);
    setAutoEntityExtraction(space.auto_entity_extraction);
    setGraphLlmId(space.graph_llm_id ?? null);
    setHasChanges(false);
  };

  const getConfigLabel = (config: CombinedConfig) => {
    const globalBadge = config.is_global ? " (Global)" : "";
    return `${config.name} - ${config.provider}/${config.model_name}${globalBadge}`;
  };

  const isLoading = isLoadingSpace || isLoadingGlobal || isLoadingCustom;

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
      <div>
        <h3 className="text-lg font-semibold">
          {t("spaces.settings.graph.title")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("spaces.settings.graph.description")}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {t("spaces.settings.graph.enableTitle")}
          </CardTitle>
          <CardDescription>
            {t("spaces.settings.graph.enableDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <Label htmlFor="enable_knowledge_graph">
            {t("spaces.settings.graph.enableLabel")}
          </Label>
          <Switch
            id="enable_knowledge_graph"
            checked={enableKnowledgeGraph}
            onCheckedChange={setEnableKnowledgeGraph}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {t("spaces.settings.graph.autoExtractTitle")}
          </CardTitle>
          <CardDescription>
            {t("spaces.settings.graph.autoExtractDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <Label htmlFor="auto_entity_extraction">
            {t("spaces.settings.graph.autoExtractLabel")}
          </Label>
          <Switch
            id="auto_entity_extraction"
            checked={autoEntityExtraction}
            onCheckedChange={setAutoEntityExtraction}
            disabled={!enableKnowledgeGraph}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {t("spaces.settings.graph.graphLLMTitle")}
          </CardTitle>
          <CardDescription>
            {t("spaces.settings.graph.graphLLMDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="graph_llm_id">
              {t("spaces.settings.graph.selectModel")}
            </Label>
            <Select
              value={graphLlmId?.toString() || ""}
              onValueChange={(value) =>
                setGraphLlmId(value ? Number(value) : null)
              }
              disabled={!enableKnowledgeGraph}
            >
              <SelectTrigger id="graph_llm_id">
                <SelectValue
                  placeholder={t("spaces.settings.graph.selectPlaceholder")}
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

      <div className="flex items-center justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={handleReset}
          disabled={!hasChanges || isUpdating}
        >
          {t("common.reset")}
        </Button>
        <Button type="button" onClick={handleSave} disabled={!hasChanges || isUpdating}>
          {isUpdating ? t("common.saving") : t("common.save")}
        </Button>
      </div>
    </div>
  );
}
