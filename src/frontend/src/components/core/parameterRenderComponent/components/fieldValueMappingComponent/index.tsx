import { ArrowRight, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { cn } from "@/utils/utils";
import type { InputProps } from "../../types";

interface ValueMappingRule {
  id: string;
  source_value: string;
  target_value: string;
  enabled: boolean;
}

interface FieldValueMapping {
  source_field: string;
  target_field: string;
  mappings: ValueMappingRule[];
  default_value: string;
}

export default function FieldValueMappingComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [config, setConfig] = useState<FieldValueMapping>({
    source_field: "",
    target_field: "",
    mappings: [],
    default_value: "",
  });

  useEffect(() => {
    if (!value) {
      setConfig({
        source_field: "",
        target_field: "",
        mappings: [],
        default_value: "",
      });
      return;
    }

    try {
      const parsed = typeof value === "string" ? JSON.parse(value) : value;
      setConfig({
        source_field: parsed.source_field || "",
        target_field: parsed.target_field || "",
        mappings: Array.isArray(parsed.mappings) ? parsed.mappings : [],
        default_value: parsed.default_value || "",
      });
    } catch (e) {
      setConfig({
        source_field: "",
        target_field: "",
        mappings: [],
        default_value: "",
      });
    }
  }, [value]);

  const updateValue = (newConfig: FieldValueMapping) => {
    handleOnNewValue({ value: JSON.stringify(newConfig) });
  };

  const handleFieldChange = (field: keyof FieldValueMapping, value: string) => {
    const newConfig = {
      ...config,
      [field]: value,
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleAddMapping = () => {
    const newMapping: ValueMappingRule = {
      id: `mapping-${Date.now()}`,
      source_value: "",
      target_value: "",
      enabled: true,
    };

    const newConfig = {
      ...config,
      mappings: [...config.mappings, newMapping],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleRemoveMapping = (id: string) => {
    const newConfig = {
      ...config,
      mappings: config.mappings.filter((m) => m.id !== id),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleUpdateMapping = (
    id: string,
    field: keyof ValueMappingRule,
    value: any,
  ) => {
    const newConfig = {
      ...config,
      mappings: config.mappings.map((m) =>
        m.id === id ? { ...m, [field]: value } : m,
      ),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const isDisabled = disabled;
  const hasMappings = config.mappings.length > 0;

  return (
    <div className="w-full">
      <div className="flex flex-col gap-3">
        {/* Source and Target Fields */}
        <div className="rounded-md border border-border bg-background p-3">
          <div className="mb-3">
            <label className="mb-2 block text-sm font-medium">
              Source Field
            </label>
            <Input
              value={config.source_field}
              onChange={(e) =>
                handleFieldChange("source_field", e.target.value)
              }
              placeholder="Field name to map from"
              disabled={isDisabled}
              className="h-9 text-sm"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">
              Target Field
            </label>
            <Input
              value={config.target_field}
              onChange={(e) =>
                handleFieldChange("target_field", e.target.value)
              }
              placeholder="Field name to map to"
              disabled={isDisabled}
              className="h-9 text-sm"
            />
          </div>
        </div>

        {/* Value Mappings Table */}
        {hasMappings && (
          <div className="rounded-md border border-border bg-background">
            <div className="grid grid-cols-[40px_1fr_40px_1fr_40px] gap-2 border-b border-border bg-muted/50 p-2 text-xs font-medium">
              <div className="flex items-center justify-center">Enabled</div>
              <div>Source Value</div>
              <div className="flex items-center justify-center">
                <ArrowRight className="h-4 w-4" />
              </div>
              <div>Target Value</div>
              <div></div>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {config.mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className={cn(
                    "grid grid-cols-[40px_1fr_40px_1fr_40px] gap-2 border-b border-border p-2 last:border-b-0",
                    !mapping.enabled && "opacity-50",
                  )}
                >
                  <div className="flex items-center justify-center">
                    <Checkbox
                      checked={mapping.enabled}
                      onCheckedChange={(checked) =>
                        handleUpdateMapping(
                          mapping.id,
                          "enabled",
                          checked as boolean,
                        )
                      }
                      disabled={isDisabled}
                    />
                  </div>

                  <Input
                    value={mapping.source_value}
                    onChange={(e) =>
                      handleUpdateMapping(
                        mapping.id,
                        "source_value",
                        e.target.value,
                      )
                    }
                    placeholder="Source value"
                    disabled={isDisabled}
                    className="h-8 text-sm"
                  />

                  <div className="flex items-center justify-center text-muted-foreground">
                    <ArrowRight className="h-4 w-4" />
                  </div>

                  <Input
                    value={mapping.target_value}
                    onChange={(e) =>
                      handleUpdateMapping(
                        mapping.id,
                        "target_value",
                        e.target.value,
                      )
                    }
                    placeholder="Target value"
                    disabled={isDisabled}
                    className="h-8 text-sm"
                  />

                  <div className="flex items-center justify-center">
                    {!isDisabled && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => handleRemoveMapping(mapping.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add Mapping Button */}
        <div className="flex items-center justify-between">
          <Button
            data-testid={`value-mapping-add-${id}`}
            disabled={isDisabled}
            variant="outline"
            size="sm"
            onClick={handleAddMapping}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Value Mapping
          </Button>
        </div>

        {/* Default Value */}
        <div className="rounded-md border border-border bg-background p-3">
          <label className="mb-2 block text-sm font-medium">
            Default Value
          </label>
          <Input
            value={config.default_value}
            onChange={(e) => handleFieldChange("default_value", e.target.value)}
            placeholder="Value to use when no mapping matches"
            disabled={isDisabled}
            className="h-9 text-sm"
          />
          <div className="mt-1 text-xs text-muted-foreground">
            This value will be used when a source value does not match any
            mapping rule
          </div>
        </div>

        {/* Info Text */}
        {hasMappings && (
          <div className="text-xs text-muted-foreground">
            {config.mappings.length} value mapping
            {config.mappings.length !== 1 ? "s" : ""} configured
          </div>
        )}
      </div>
    </div>
  );
}
