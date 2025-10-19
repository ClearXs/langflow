import { Code, Database, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/utils/utils";
import type { InputProps } from "../../types";

interface FieldMapping {
  id: string;
  source_field: string;
  target_field: string;
  data_type: string;
  transformation_rule: string | { type: string; content: string };
  default_value: string;
  enabled: boolean;
}

// Data type options
const DATA_TYPES = [
  { value: "string", label: "String" },
  { value: "integer", label: "Integer" },
  { value: "float", label: "Float" },
  { value: "decimal", label: "Decimal" },
  { value: "boolean", label: "Boolean" },
  { value: "date", label: "Date" },
  { value: "datetime", label: "DateTime" },
  { value: "timestamp", label: "Timestamp" },
  { value: "json", label: "JSON" },
  { value: "text", label: "Text" },
];

// Transformation rule options
const TRANSFORMATION_RULES = [
  { value: "none", label: "None" },
  { value: "upper", label: "To Uppercase" },
  { value: "lower", label: "To Lowercase" },
  { value: "trim", label: "Trim Spaces" },
  { value: "mask_phone", label: "Mask Phone" },
  { value: "mask_idcard", label: "Mask ID Card" },
  { value: "mask_email", label: "Mask Email" },
  { value: "mask_name", label: "Mask Name" },
  { value: "md5", label: "MD5 Hash" },
  { value: "sha256", label: "SHA256 Hash" },
  { value: "to_int", label: "To Integer" },
  { value: "to_float", label: "To Float" },
  { value: "to_str", label: "To String" },
  { value: "to_bool", label: "To Boolean" },
  { value: "expression", label: "Expression" },
  { value: "javascript", label: "JavaScript" },
  { value: "python", label: "Python Script" },
];

export default function EnhancedFieldMappingComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
  tableSchema,
}: InputProps<string | any[], any>): JSX.Element {
  const { t } = useTranslation();
  const [mappings, setMappings] = useState<FieldMapping[]>([]);
  const [scriptModalOpen, setScriptModalOpen] = useState(false);
  const [currentScript, setCurrentScript] = useState({
    id: "",
    type: "",
    content: "",
  });

  // Get available columns from tableSchema
  const sourceFieldOptions = tableSchema?.[0]?.options || [];

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
        source_field: m.source_field || "",
        target_field: m.target_field || "",
        data_type: m.data_type || "string",
        transformation_rule: m.transformation_rule || "none",
        default_value: m.default_value || "",
        enabled: m.enabled !== undefined ? m.enabled : true,
      }));

      setMappings(formattedMappings);
    } catch (e) {
      console.error("Error parsing field mappings:", e);
      setMappings([]);
    }
  }, [value]);

  const updateValue = useCallback(
    (newMappings: FieldMapping[]) => {
      handleOnNewValue(newMappings, { skipSnapshot: false });
    },
    [handleOnNewValue],
  );

  const handleAddMapping = () => {
    const newMapping: FieldMapping = {
      id: `mapping-${Date.now()}`,
      source_field: "",
      target_field: "",
      data_type: "string",
      transformation_rule: "none",
      default_value: "",
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

  const handleTransformationRuleChange = (id: string, value: string) => {
    if (value === "expression") {
      // Open expression editor
      setCurrentScript({ id, type: "expression", content: "" });
      setScriptModalOpen(true);
    } else if (value === "javascript" || value === "python") {
      // Open script editor
      setCurrentScript({ id, type: value, content: "" });
      setScriptModalOpen(true);
    } else {
      // Simple transformation
      handleUpdateMapping(id, "transformation_rule", value);
    }
  };

  const handleScriptSave = () => {
    if (currentScript.id) {
      const rule = {
        type: currentScript.type,
        content: currentScript.content,
      };
      handleUpdateMapping(currentScript.id, "transformation_rule", rule);
    }
    setScriptModalOpen(false);
    setCurrentScript({ id: "", type: "", content: "" });
  };

  const getTransformationLabel = (rule: string | any) => {
    if (typeof rule === "string") {
      const found = TRANSFORMATION_RULES.find((r) => r.value === rule);
      return found ? found.label : rule;
    } else if (rule && typeof rule === "object") {
      return rule.type === "expression"
        ? "Expression"
        : rule.type === "javascript"
          ? "JavaScript"
          : rule.type === "python"
            ? "Python Script"
            : "Custom";
    }
    return "None";
  };

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {t("fieldMapper.mappingsCount", {
            count: mappings.filter((m) => m.enabled).length,
          })}
        </div>
        <Button
          onClick={handleAddMapping}
          size="sm"
          variant="outline"
          disabled={disabled}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t("fieldMapper.addMapping")}
        </Button>
      </div>

      {/* Mappings Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b">
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.enabled")}
              </th>
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.sourceField")}
              </th>
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.targetField")}
              </th>
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.dataType")}
              </th>
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.transformationRule")}
              </th>
              <th className="p-2 text-left text-xs font-medium">
                {t("fieldMapper.defaultValue")}
              </th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((mapping) => (
              <tr key={mapping.id} className="border-b">
                <td className="p-2">
                  <Checkbox
                    checked={mapping.enabled}
                    onCheckedChange={(checked) =>
                      handleUpdateMapping(mapping.id, "enabled", checked)
                    }
                    disabled={disabled}
                  />
                </td>
                <td className="p-2">
                  {sourceFieldOptions.length > 0 ? (
                    <Select
                      value={mapping.source_field}
                      onValueChange={(val) =>
                        handleUpdateMapping(mapping.id, "source_field", val)
                      }
                      disabled={disabled || !mapping.enabled}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue
                          placeholder={t("fieldMapper.sourceFieldPlaceholder")}
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {sourceFieldOptions.map((opt: any) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      value={mapping.source_field}
                      onChange={(e) =>
                        handleUpdateMapping(
                          mapping.id,
                          "source_field",
                          e.target.value,
                        )
                      }
                      placeholder={t("fieldMapper.sourceFieldPlaceholder")}
                      className="h-8"
                      disabled={disabled || !mapping.enabled}
                    />
                  )}
                </td>
                <td className="p-2">
                  <Input
                    value={mapping.target_field}
                    onChange={(e) =>
                      handleUpdateMapping(
                        mapping.id,
                        "target_field",
                        e.target.value,
                      )
                    }
                    placeholder={t("fieldMapper.targetFieldPlaceholder")}
                    className="h-8"
                    disabled={disabled || !mapping.enabled}
                  />
                </td>
                <td className="p-2">
                  <Select
                    value={mapping.data_type}
                    onValueChange={(val) =>
                      handleUpdateMapping(mapping.id, "data_type", val)
                    }
                    disabled={disabled || !mapping.enabled}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DATA_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </td>
                <td className="p-2">
                  <div className="flex items-center gap-1">
                    <Select
                      value={
                        typeof mapping.transformation_rule === "string"
                          ? mapping.transformation_rule
                          : "custom"
                      }
                      onValueChange={(val) =>
                        handleTransformationRuleChange(mapping.id, val)
                      }
                      disabled={disabled || !mapping.enabled}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue>
                          {getTransformationLabel(mapping.transformation_rule)}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {TRANSFORMATION_RULES.map((rule) => (
                          <SelectItem key={rule.value} value={rule.value}>
                            {rule.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {(typeof mapping.transformation_rule === "object" ||
                      ["expression", "javascript", "python"].includes(
                        mapping.transformation_rule as string,
                      )) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          const rule = mapping.transformation_rule;
                          if (typeof rule === "object") {
                            setCurrentScript({
                              id: mapping.id,
                              type: rule.type,
                              content: rule.content,
                            });
                          } else {
                            setCurrentScript({
                              id: mapping.id,
                              type: rule as string,
                              content: "",
                            });
                          }
                          setScriptModalOpen(true);
                        }}
                        disabled={disabled || !mapping.enabled}
                      >
                        <Code className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </td>
                <td className="p-2">
                  <Input
                    value={mapping.default_value}
                    onChange={(e) =>
                      handleUpdateMapping(
                        mapping.id,
                        "default_value",
                        e.target.value,
                      )
                    }
                    placeholder={t("fieldMapper.defaultValuePlaceholder")}
                    className="h-8"
                    disabled={disabled || !mapping.enabled}
                  />
                </td>
                <td className="p-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRemoveMapping(mapping.id)}
                    disabled={disabled}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Script Editor Modal */}
      <Dialog open={scriptModalOpen} onOpenChange={setScriptModalOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {currentScript.type === "expression" &&
                t("transformation.editor.expression")}
              {currentScript.type === "javascript" &&
                t("transformation.editor.javascript")}
              {currentScript.type === "python" &&
                t("transformation.editor.python")}
            </DialogTitle>
            <DialogDescription>
              {currentScript.type === "expression" && (
                <div className="space-y-2 text-sm">
                  <p>{t("transformation.editor.expressionHelp")}</p>
                  <ul className="list-disc pl-5">
                    <li>
                      Use ${"{"}field_name{"}"} to reference other fields
                    </li>
                    <li>
                      Use ${"{"}value{"}"} for the current field value
                    </li>
                    <li>
                      Example: ${"{"}price{"}"} * 1.1
                    </li>
                  </ul>
                </div>
              )}
              {(currentScript.type === "javascript" ||
                currentScript.type === "python") && (
                <div className="space-y-2 text-sm">
                  <p>{t("transformation.editor.scriptHelp")}</p>
                  <ul className="list-disc pl-5">
                    <li>
                      Available variables: value (current value), row (full row
                      data)
                    </li>
                    <li>
                      {currentScript.type === "javascript"
                        ? "Return the transformed value"
                        : "Set result = transformed value"}
                    </li>
                  </ul>
                </div>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              value={currentScript.content}
              onChange={(e) =>
                setCurrentScript({ ...currentScript, content: e.target.value })
              }
              placeholder={
                currentScript.type === "expression"
                  ? "${value} * 2"
                  : currentScript.type === "javascript"
                    ? "if (value > 100) return value * 0.9;\nreturn value;"
                    : "# Python script\nif value > 100:\n    result = value * 0.9\nelse:\n    result = value"
              }
              className="min-h-[200px] font-mono"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setScriptModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleScriptSave}>{t("common.save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {mappings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Database className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {t("fieldMapper.noMappings")}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("fieldMapper.clickToAdd")}
          </p>
        </div>
      )}
    </div>
  );
}
