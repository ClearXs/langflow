import { Download, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { usePostTemplateValue } from "@/controllers/API/queries/nodes/use-post-template-value";
import { cn } from "@/utils/utils";
import type { InputProps } from "../../types";

interface ConditionRow {
  id: string;
  field_name: string;
  operator: string;
  compare_value: string;
  enabled: boolean;
}

interface ConditionalRouterConfig {
  combination_logic: "AND" | "OR";
  conditions: ConditionRow[];
}

const STRING_OPERATORS = [
  { value: "equals", label: "equals" },
  { value: "not equals", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "starts with", label: "starts with" },
  { value: "ends with", label: "ends with" },
  { value: "regex", label: "regex" },
  { value: "is empty", label: "is empty" },
  { value: "is not empty", label: "is not empty" },
  { value: "in list", label: "in list" },
  { value: "not in list", label: "not in list" },
] as const;

const NUMERIC_OPERATORS = [
  { value: "equals", label: "equals" },
  { value: "not equals", label: "not equals" },
  { value: "less than", label: "less than" },
  { value: "less than or equal", label: "less than or equal" },
  { value: "greater than", label: "greater than" },
  { value: "greater than or equal", label: "greater than or equal" },
  { value: "is empty", label: "is empty" },
  { value: "is not empty", label: "is not empty" },
] as const;

const BOOLEAN_OPERATORS = [
  { value: "equals", label: "equals" },
  { value: "not equals", label: "not equals" },
  { value: "is empty", label: "is empty" },
  { value: "is not empty", label: "is not empty" },
] as const;

export default function ConditionalRouterTableInputComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
  fieldSchema,
  nodeId,
  nodeClass,
  handleNodeClass,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [config, setConfig] = useState<ConditionalRouterConfig>({
    combination_logic: "AND",
    conditions: [],
  });

  const [fieldOptions, setFieldOptions] = useState<
    Array<{ value: string; label: string; type?: string }>
  >([]);
  const [fieldTypes, setFieldTypes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // API hook for action button triggers
  const templateValueMutation = usePostTemplateValue({
    parameterId: id,
    nodeId: nodeId,
    node: nodeClass,
  });

  useEffect(() => {
    if (!value) {
      setConfig({ combination_logic: "AND", conditions: [] });
      return;
    }

    try {
      const parsed = typeof value === "string" ? JSON.parse(value) : value;
      setConfig({
        combination_logic: parsed.combination_logic || "AND",
        conditions: Array.isArray(parsed.conditions) ? parsed.conditions : [],
      });
    } catch (e) {
      setConfig({ combination_logic: "AND", conditions: [] });
    }
  }, [value]);

  useEffect(() => {
    // Extract field types and options from fieldSchema
    if (fieldSchema) {
      const fieldColumn = fieldSchema.find(
        (col: any) => col.name === "field_name",
      );
      if (fieldColumn) {
        setFieldOptions(fieldColumn.options || []);
        setFieldTypes(fieldColumn.field_types || {});
      }
    }
  }, [fieldSchema]);

  const updateValue = (newConfig: ConditionalRouterConfig) => {
    handleOnNewValue({ value: JSON.stringify(newConfig) });
  };

  const handleLoadFields = async () => {
    setLoading(true);
    try {
      const response = await templateValueMutation.mutateAsync({
        action: "load_fields",
        field_name: "conditions",
        value: "", // Required by the interface, but may not be used for action
      });

      if (response?.template?.field_names) {
        const fields = response.template.field_names.map((name: string) => ({
          value: name,
          label: name,
        }));
        setFieldOptions(fields);

        if (response.template.field_types) {
          setFieldTypes(response.template.field_types);
        }
      }
    } catch (error) {
      console.error("Failed to load fields:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCondition = () => {
    const newCondition: ConditionRow = {
      id: `condition-${Date.now()}`,
      field_name: "",
      operator: "equals",
      compare_value: "",
      enabled: true,
    };

    const newConfig = {
      ...config,
      conditions: [...config.conditions, newCondition],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleRemoveCondition = (id: string) => {
    const newConfig = {
      ...config,
      conditions: config.conditions.filter((c) => c.id !== id),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleUpdateCondition = (
    id: string,
    field: keyof ConditionRow,
    value: any,
  ) => {
    const newConfig = {
      ...config,
      conditions: config.conditions.map((condition) =>
        condition.id === id ? { ...condition, [field]: value } : condition,
      ),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const getOperatorsForField = (fieldName: string) => {
    const fieldType = fieldTypes[fieldName];
    switch (fieldType) {
      case "number":
        return NUMERIC_OPERATORS;
      case "boolean":
        return BOOLEAN_OPERATORS;
      default:
        return STRING_OPERATORS;
    }
  };

  const toggleCondition = (id: string) => {
    const newConfig = {
      ...config,
      conditions: config.conditions.map((condition) =>
        condition.id === id
          ? { ...condition, enabled: !condition.enabled }
          : condition,
      ),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  return (
    <div className="space-y-4">
      {/* Combination Logic Selection */}
      <div className="flex items-center space-x-4">
        <label className="text-sm font-medium">
          {t(
            "components.logic.conditional_router.combination_logic.display_name",
          )}
          :
        </label>
        <Select
          value={config.combination_logic}
          onValueChange={(value: "AND" | "OR") => {
            const newConfig = { ...config, combination_logic: value };
            setConfig(newConfig);
            updateValue(newConfig);
          }}
          disabled={disabled}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="AND">AND</SelectItem>
            <SelectItem value="OR">OR</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={handleLoadFields}
          disabled={disabled || loading}
          className="flex items-center space-x-2"
        >
          <Download className="w-4 h-4" />
          <span>
            {t(
              "components.logic.conditional_router.conditions.load_fields_button",
            )}
          </span>
        </Button>
      </div>

      {/* Conditions Table */}
      <div className="border rounded-lg">
        <div className="grid grid-cols-12 gap-2 p-3 border-b bg-gray-50 dark:bg-gray-800">
          <div className="col-span-1 text-xs font-medium text-center">
            {t("common.enabled")}
          </div>
          <div className="col-span-3 text-xs font-medium">
            {t("components.logic.conditional_router.conditions.field_name")}
          </div>
          <div className="col-span-3 text-xs font-medium">
            {t("components.logic.conditional_router.conditions.operator")}
          </div>
          <div className="col-span-4 text-xs font-medium">
            {t("components.logic.conditional_router.conditions.compare_value")}
          </div>
          <div className="col-span-1 text-xs font-medium text-center">
            {t("common.actions")}
          </div>
        </div>

        {config.conditions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            {t("components.logic.conditional_router.no_conditions_added")}
          </div>
        ) : (
          <div className="max-h-64 overflow-y-auto">
            {config.conditions.map((condition, index) => (
              <div
                key={condition.id}
                className={cn(
                  "grid grid-cols-12 gap-2 p-3 border-b last:border-b-0",
                  !condition.enabled && "opacity-50",
                )}
              >
                {/* Enabled Checkbox */}
                <div className="col-span-1 flex items-center justify-center">
                  <input
                    type="checkbox"
                    checked={condition.enabled}
                    onChange={() => toggleCondition(condition.id)}
                    disabled={disabled}
                    className="rounded border-gray-300"
                  />
                </div>

                {/* Field Name */}
                <div className="col-span-3">
                  <Select
                    value={condition.field_name}
                    onValueChange={(value) =>
                      handleUpdateCondition(condition.id, "field_name", value)
                    }
                    disabled={disabled || !condition.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue
                        placeholder={t(
                          "components.logic.conditional_router.select_field",
                        )}
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {fieldOptions.map((field) => (
                        <SelectItem key={field.value} value={field.value}>
                          {field.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Operator */}
                <div className="col-span-3">
                  <Select
                    value={condition.operator}
                    onValueChange={(value) =>
                      handleUpdateCondition(condition.id, "operator", value)
                    }
                    disabled={disabled || !condition.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue
                        placeholder={t(
                          "components.logic.conditional_router.select_operator",
                        )}
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {getOperatorsForField(condition.field_name).map(
                        (operator) => (
                          <SelectItem
                            key={operator.value}
                            value={operator.value}
                          >
                            {operator.label}
                          </SelectItem>
                        ),
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Compare Value */}
                <div className="col-span-4">
                  <Input
                    value={condition.compare_value}
                    onChange={(e) =>
                      handleUpdateCondition(
                        condition.id,
                        "compare_value",
                        e.target.value,
                      )
                    }
                    disabled={disabled || !condition.enabled}
                    placeholder={
                      condition.operator === "in list" ||
                      condition.operator === "not in list"
                        ? t(
                            "components.logic.conditional_router.list_placeholder",
                          )
                        : t(
                            "components.logic.conditional_router.value_placeholder",
                          )
                    }
                  />
                </div>

                {/* Actions */}
                <div className="col-span-1 flex items-center justify-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveCondition(condition.id)}
                    disabled={disabled}
                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Condition Button */}
      <Button
        variant="outline"
        onClick={handleAddCondition}
        disabled={disabled}
        className="w-full flex items-center justify-center space-x-2"
      >
        <Plus className="w-4 h-4" />
        <span>{t("components.logic.conditional_router.add_condition")}</span>
      </Button>

      {/* Instructions */}
      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
        <p>
          {t(
            "components.logic.conditional_router.instructions.field_selection",
          )}
        </p>
        <p>
          {t(
            "components.logic.conditional_router.instructions.operator_selection",
          )}
        </p>
        <p>
          {t("components.logic.conditional_router.instructions.list_format")}
        </p>
      </div>
    </div>
  );
}
