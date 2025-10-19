import { ArrowRight, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/utils/utils";
import type { InputProps } from "../../types";

interface FieldMapping {
  id: string;
  src_col: string;
  tgt_col: string;
  tgt_type: string;
  tgt_unit: string;
  enabled: boolean;
}

const DATA_TYPES = ["string", "integer", "float", "boolean"];

export default function FieldMappingTableInputComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [mappings, setMappings] = useState<FieldMapping[]>([]);

  useEffect(() => {
    if (!value) {
      setMappings([]);
      return;
    }

    try {
      const parsed = typeof value === "string" ? JSON.parse(value) : value;
      const mappingsArray = Array.isArray(parsed) ? parsed : [];

      const formattedMappings = mappingsArray.map((m: any, idx: number) => ({
        id: m.id || `mapping-${idx}`,
        src_col: m.src_col || "",
        tgt_col: m.tgt_col || "",
        tgt_type: m.tgt_type || "string",
        tgt_unit: m.tgt_unit || "",
        enabled: m.enabled !== undefined ? m.enabled : true,
      }));

      setMappings(formattedMappings);
    } catch (e) {
      setMappings([]);
    }
  }, [value]);

  const handleAddMapping = () => {
    const newMapping: FieldMapping = {
      id: `mapping-${Date.now()}`,
      src_col: "",
      tgt_col: "",
      tgt_type: "string",
      tgt_unit: "",
      enabled: true,
    };

    const newMappings = [...mappings, newMapping];
    setMappings(newMappings);
    updateValue(newMappings);
  };

  const handleRemoveMapping = (id: string) => {
    const newMappings = mappings.filter((m) => m.id !== id);
    setMappings(newMappings);
    updateValue(newMappings);
  };

  const handleUpdateMapping = (
    id: string,
    field: keyof FieldMapping,
    value: any,
  ) => {
    const newMappings = mappings.map((m) =>
      m.id === id ? { ...m, [field]: value } : m,
    );
    setMappings(newMappings);
    updateValue(newMappings);
  };

  const updateValue = (newMappings: FieldMapping[]) => {
    handleOnNewValue({ value: JSON.stringify(newMappings) });
  };

  const isDisabled = disabled;
  const hasMappings = mappings.length > 0;

  return (
    <div className="w-full">
      <div className="flex flex-col gap-3">
        {hasMappings && (
          <div className="rounded-md border border-border bg-background">
            <div className="grid grid-cols-[40px_1fr_40px_1fr_120px_120px_40px] gap-2 border-b border-border bg-muted/50 p-2 text-xs font-medium">
              <div className="flex items-center justify-center">
                {t("fieldMapper.enabled")}
              </div>
              <div>{t("fieldMapper.sourceField")}</div>
              <div className="flex items-center justify-center">
                <ArrowRight className="h-4 w-4" />
              </div>
              <div>{t("fieldMapper.targetField")}</div>
              <div>{t("fieldMapper.type")}</div>
              <div>{t("fieldMapper.unit")}</div>
              <div></div>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className={cn(
                    "grid grid-cols-[40px_1fr_40px_1fr_120px_120px_40px] gap-2 border-b border-border p-2 last:border-b-0",
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
                    value={mapping.src_col}
                    onChange={(e) =>
                      handleUpdateMapping(mapping.id, "src_col", e.target.value)
                    }
                    placeholder={t("fieldMapper.sourceFieldPlaceholder")}
                    disabled={isDisabled}
                    className="h-8 text-sm"
                  />

                  <div className="flex items-center justify-center text-muted-foreground">
                    <ArrowRight className="h-4 w-4" />
                  </div>

                  <Input
                    value={mapping.tgt_col}
                    onChange={(e) =>
                      handleUpdateMapping(mapping.id, "tgt_col", e.target.value)
                    }
                    placeholder={t("fieldMapper.targetFieldPlaceholder")}
                    disabled={isDisabled}
                    className="h-8 text-sm"
                  />

                  <Select
                    value={mapping.tgt_type}
                    onValueChange={(value) =>
                      handleUpdateMapping(mapping.id, "tgt_type", value)
                    }
                    disabled={isDisabled}
                  >
                    <SelectTrigger className="h-8 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DATA_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Input
                    value={mapping.tgt_unit}
                    onChange={(e) =>
                      handleUpdateMapping(
                        mapping.id,
                        "tgt_unit",
                        e.target.value,
                      )
                    }
                    placeholder={t("fieldMapper.unitPlaceholder")}
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

        <div className="flex items-center justify-between">
          <Button
            data-testid={`field-mapping-add-${id}`}
            disabled={isDisabled}
            variant="outline"
            size="sm"
            onClick={handleAddMapping}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("fieldMapper.addMapping")}
          </Button>
        </div>

        {hasMappings && (
          <div className="text-xs text-muted-foreground">
            {t("fieldMapper.mappingsCount", { count: mappings.length })}
          </div>
        )}
      </div>
    </div>
  );
}
