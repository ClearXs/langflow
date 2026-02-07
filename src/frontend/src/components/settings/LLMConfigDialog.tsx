import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  useGetDefaultSystemInstructionsQuery,
  usePostCreateLLMConfig,
  usePutUpdateLLMConfig,
} from "@/controllers/API/queries/llm-configs";
import type {
  LLMConfigCreate,
  LLMConfigRead,
  LLMConfigUpdate,
} from "@/types/api/llm-configs";

interface LLMConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  spaceId: number;
  config?: LLMConfigRead | null;
  onSuccess: () => void;
}

interface FormData {
  name: string;
  provider: string;
  model_name: string;
  api_key: string;
  api_base: string;
  system_instructions: string;
  use_default_system_instructions: boolean;
  citations_enabled: boolean;
}

// Common providers
const PROVIDERS = [
  { value: "openai", label: "OpenAI", requiresKey: true },
  { value: "anthropic", label: "Anthropic", requiresKey: true },
  {
    value: "azure",
    label: "Azure OpenAI",
    requiresKey: true,
    requiresBase: true,
  },
  { value: "groq", label: "Groq", requiresKey: true },
  { value: "deepseek", label: "DeepSeek", requiresKey: true },
  { value: "openrouter", label: "OpenRouter", requiresKey: true },
  {
    value: "ollama",
    label: "Ollama (Local)",
    requiresKey: false,
    requiresBase: true,
  },
  { value: "custom", label: "Custom", requiresKey: true, requiresBase: true },
];

export default function LLMConfigDialog({
  open,
  onOpenChange,
  spaceId,
  config,
  onSuccess,
}: LLMConfigDialogProps) {
  const { t } = useTranslation();
  const isEditing = !!config;

  const { data: defaultInstructionsResponse } =
    useGetDefaultSystemInstructionsQuery();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: "",
      provider: "openai",
      model_name: "",
      api_key: "",
      api_base: "",
      system_instructions: "",
      use_default_system_instructions: true,
      citations_enabled: true,
    },
  });

  const selectedProvider = watch("provider");
  const useDefaultInstructions = watch("use_default_system_instructions");

  const providerInfo = PROVIDERS.find((p) => p.value === selectedProvider);

  const { mutateAsync: createConfig, isPending: isCreating } =
    usePostCreateLLMConfig();
  const { mutateAsync: updateConfig, isPending: isUpdating } =
    usePutUpdateLLMConfig();

  const isPending = isCreating || isUpdating;

  // Populate form when editing
  useEffect(() => {
    if (config) {
      reset({
        name: config.name,
        provider: config.provider,
        model_name: config.model_name,
        api_key: config.api_key || "",
        api_base: config.api_base || "",
        system_instructions: config.system_instructions || "",
        use_default_system_instructions: config.use_default_system_instructions,
        citations_enabled: config.citations_enabled,
      });
    } else {
      reset({
        name: "",
        provider: "openai",
        model_name: "",
        api_key: "",
        api_base: "",
        system_instructions: "",
        use_default_system_instructions: true,
        citations_enabled: true,
      });
    }
  }, [config, reset]);

  // Update system instructions when toggle changes
  useEffect(() => {
    if (useDefaultInstructions && defaultInstructionsResponse) {
      setValue("system_instructions", defaultInstructionsResponse.instructions);
    }
  }, [useDefaultInstructions, defaultInstructionsResponse, setValue]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEditing && config) {
        const updateData: LLMConfigUpdate = {
          name: data.name,
          provider: data.provider,
          model_name: data.model_name,
          api_key: data.api_key || null,
          api_base: data.api_base || null,
          system_instructions: data.system_instructions || null,
          use_default_system_instructions: data.use_default_system_instructions,
          citations_enabled: data.citations_enabled,
        };

        await updateConfig({
          configId: config.id,
          data: updateData,
        });

        toast.success(t("spaces.settings.configUpdated"));
      } else {
        const createData: LLMConfigCreate = {
          search_space_id: spaceId,
          name: data.name,
          provider: data.provider,
          model_name: data.model_name,
          api_key: data.api_key || null,
          api_base: data.api_base || null,
          system_instructions: data.system_instructions || null,
          use_default_system_instructions: data.use_default_system_instructions,
          citations_enabled: data.citations_enabled,
        };

        await createConfig(createData);

        toast.success(t("spaces.settings.configCreated"));
      }

      onSuccess();
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.detail ||
        error?.message ||
        t("spaces.settings.configSaveError");
      toast.error(errorMessage);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing
              ? t("spaces.settings.editConfig")
              : t("spaces.settings.createConfig")}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? t("spaces.settings.editConfigDescription")
              : t("spaces.settings.createConfigDescription")}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              {t("spaces.settings.configName")}{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              {...register("name", {
                required: t("spaces.settings.nameRequired"),
              })}
              value={watch("name")}
              placeholder={t("spaces.settings.configNamePlaceholder")}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Provider */}
          <div className="space-y-2">
            <Label htmlFor="provider">
              {t("spaces.settings.provider")}{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Select
              value={selectedProvider}
              onValueChange={(value) => setValue("provider", value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-[300px]">
                {PROVIDERS.map((provider) => (
                  <SelectItem key={provider.value} value={provider.value}>
                    {provider.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Model Name */}
          <div className="space-y-2">
            <Label htmlFor="model_name">
              {t("spaces.settings.modelName")}{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Input
              id="model_name"
              {...register("model_name", {
                required: t("spaces.settings.modelNameRequired"),
              })}
              value={watch("model_name")}
              placeholder={t("spaces.settings.modelNamePlaceholder")}
            />
            {errors.model_name && (
              <p className="text-sm text-destructive">
                {errors.model_name.message}
              </p>
            )}
          </div>

          {/* API Key */}
          {providerInfo?.requiresKey && (
            <div className="space-y-2">
              <Label htmlFor="api_key">
                {t("spaces.settings.apiKey")}{" "}
                <span className="text-destructive">*</span>
              </Label>
              <Input
                id="api_key"
                type="password"
                {...register("api_key", {
                  required: providerInfo.requiresKey
                    ? t("spaces.settings.apiKeyRequired")
                    : false,
                })}
                value={watch("api_key")}
                placeholder={t("spaces.settings.apiKeyPlaceholder")}
              />
              {errors.api_key && (
                <p className="text-sm text-destructive">
                  {errors.api_key.message}
                </p>
              )}
            </div>
          )}

          {/* API Base */}
          {providerInfo?.requiresBase && (
            <div className="space-y-2">
              <Label htmlFor="api_base">
                {t("spaces.settings.apiBase")}{" "}
                {providerInfo.requiresBase && (
                  <span className="text-destructive">*</span>
                )}
              </Label>
              <Input
                id="api_base"
                {...register("api_base", {
                  required: providerInfo.requiresBase
                    ? t("spaces.settings.apiBaseRequired")
                    : false,
                })}
                value={watch("api_base")}
                placeholder="https://api.example.com/v1"
              />
              {errors.api_base && (
                <p className="text-sm text-destructive">
                  {errors.api_base.message}
                </p>
              )}
            </div>
          )}

          {/* System Instructions */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="system_instructions">
                {t("spaces.settings.systemInstructions")}
              </Label>
              <div className="flex items-center gap-2">
                <Switch
                  id="use_default"
                  checked={useDefaultInstructions}
                  onCheckedChange={(checked) =>
                    setValue("use_default_system_instructions", checked)
                  }
                />
                <Label htmlFor="use_default" className="text-sm font-normal">
                  {t("spaces.settings.useDefault")}
                </Label>
              </div>
            </div>
            <Textarea
              id="system_instructions"
              {...register("system_instructions")}
              placeholder={t("spaces.settings.systemInstructionsPlaceholder")}
              rows={4}
              disabled={useDefaultInstructions}
            />
          </div>

          {/* Citations */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="citations">
                {t("spaces.settings.citationsEnabled")}
              </Label>
              <p className="text-sm text-muted-foreground">
                {t("spaces.settings.citationsDescription")}
              </p>
            </div>
            <Switch
              id="citations"
              checked={watch("citations_enabled")}
              onCheckedChange={(checked) =>
                setValue("citations_enabled", checked)
              }
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending
                ? isEditing
                  ? t("common.updating")
                  : t("common.creating")
                : isEditing
                  ? t("common.update")
                  : t("common.create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
