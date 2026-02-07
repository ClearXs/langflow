import { Pencil, Plus, Settings2, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useDeleteLLMConfig,
  useGetGlobalLLMConfigsQuery,
  useGetLLMConfigsQuery,
} from "@/controllers/API/queries/llm-configs";
import type { LLMConfigRead } from "@/types/api/llm-configs";
import LLMConfigDialog from "./LLMConfigDialog";

interface ModelConfigManagerProps {
  spaceId: number;
}

export default function ModelConfigManager({
  spaceId,
}: ModelConfigManagerProps) {
  const { t } = useTranslation();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfigRead | null>(
    null,
  );
  const [deletingConfigId, setDeletingConfigId] = useState<number | null>(null);

  // Fetch custom configs for this space
  const {
    data: customConfigs = [],
    isLoading: isLoadingCustom,
    refetch: refetchCustom,
  } = useGetLLMConfigsQuery({}, { searchSpaceId: spaceId });

  // Fetch global configs from YAML
  const { data: globalConfigs = [], isLoading: isLoadingGlobal } =
    useGetGlobalLLMConfigsQuery();

  const { mutateAsync: deleteConfig, isPending: isDeleting } =
    useDeleteLLMConfig();

  const handleDeleteConfig = async () => {
    if (!deletingConfigId) return;

    try {
      await deleteConfig({
        configId: deletingConfigId,
      });
      toast.success(t("spaces.settings.configDeleted"));
      refetchCustom();
    } catch (error) {
      toast.error(t("spaces.settings.configDeleteError"));
    } finally {
      setDeletingConfigId(null);
    }
  };

  const handleEditConfig = (config: LLMConfigRead) => {
    setEditingConfig(config);
  };

  const handleConfigSaved = () => {
    setIsCreateDialogOpen(false);
    setEditingConfig(null);
    refetchCustom();
  };

  const isLoading = isLoadingCustom || isLoadingGlobal;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            {t("spaces.settings.modelConfigsTitle")}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t("spaces.settings.modelConfigsDescription")}
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("spaces.settings.addConfig")}
        </Button>
      </div>

      {/* Global Configs Section */}
      {globalConfigs.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            <h4 className="font-medium text-sm">
              {t("spaces.settings.globalConfigs")}
            </h4>
            <Badge variant="secondary" className="text-xs">
              {t("spaces.settings.readOnly")}
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {globalConfigs.map((config) => (
              <Card key={`global-${config.id}`} className="border-dashed">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base line-clamp-1">
                        {config.name}
                      </CardTitle>
                      <CardDescription className="text-xs mt-1">
                        {config.provider}
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="ml-2 shrink-0">
                      {t("common.global")}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pb-4">
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {t("spaces.settings.model")}:
                      </span>
                      <span className="truncate">{config.model_name}</span>
                    </div>
                    {config.api_base && (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {t("spaces.settings.apiBase")}:
                        </span>
                        <span className="truncate text-xs">
                          {config.api_base}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Custom Configs Section */}
      <div className="space-y-3">
        <h4 className="font-medium text-sm">
          {t("spaces.settings.customConfigs")}
        </h4>

        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-5 bg-muted rounded w-3/4" />
                  <div className="h-4 bg-muted rounded w-1/2 mt-2" />
                </CardHeader>
                <CardContent>
                  <div className="h-16 bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!isLoading && customConfigs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 px-8 border-2 border-dashed rounded-lg">
            <div className="rounded-full bg-muted p-4 mb-4">
              <Settings2 className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-base font-semibold mb-2">
              {t("spaces.settings.noConfigsYet")}
            </h3>
            <p className="text-sm text-muted-foreground text-center max-w-sm mb-6">
              {t("spaces.settings.createFirstConfig")}
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              {t("spaces.settings.addConfig")}
            </Button>
          </div>
        )}

        {!isLoading && customConfigs.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {customConfigs.map((config) => (
              <Card
                key={config.id}
                className="hover:shadow-md transition-shadow"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base line-clamp-1">
                        {config.name}
                      </CardTitle>
                      <CardDescription className="text-xs mt-1">
                        {config.provider}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pb-3">
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {t("spaces.settings.model")}:
                      </span>
                      <span className="truncate">{config.model_name}</span>
                    </div>
                    {config.api_base && (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {t("spaces.settings.apiBase")}:
                        </span>
                        <span className="truncate text-xs">
                          {config.api_base}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {t("spaces.settings.citations")}:
                      </span>
                      <span>
                        {config.citations_enabled
                          ? t("common.enabled")
                          : t("common.disabled")}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-4 pt-3 border-t">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditConfig(config)}
                      className="flex-1"
                    >
                      <Pencil className="mr-2 h-3 w-3" />
                      {t("common.edit")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeletingConfigId(config.id)}
                      className="flex-1 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="mr-2 h-3 w-3" />
                      {t("common.delete")}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <LLMConfigDialog
        open={isCreateDialogOpen || !!editingConfig}
        onOpenChange={(open) => {
          if (!open) {
            setIsCreateDialogOpen(false);
            setEditingConfig(null);
          }
        }}
        spaceId={spaceId}
        config={editingConfig}
        onSuccess={handleConfigSaved}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deletingConfigId}
        onOpenChange={(open) => !open && setDeletingConfigId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("spaces.settings.confirmDeleteTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("spaces.settings.confirmDeleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfig}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? t("common.deleting") : t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
