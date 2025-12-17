import type { CustomCellEditorProps } from "ag-grid-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import InputComponent from "../../../inputComponent";

interface OptionMetadata {
  value: string;
  label: string;
}

export default function TableDropdownCellEditor({
  value,
  values,
  optionsMetadata,
  optionsMap,
  dependOn,
  data,
  onValueChange,
  colDef,
  eGridCell,
}: CustomCellEditorProps & {
  values: string[];
  optionsMetadata?: OptionMetadata[];
  optionsMap?: Record<string, OptionMetadata[]>;
  dependOn?: string;
  data?: any;
}) {
  const { t } = useTranslation();

  // Determine which options to use based on optionsMap and dependOn
  const effectiveOptionsMetadata = useMemo(() => {
    // If optionsMap and dependOn are configured, use dynamic options
    if (optionsMap && dependOn && data) {
      const dependentValue = data[dependOn];

      if (dependentValue && optionsMap[dependentValue]) {
        return optionsMap[dependentValue];
      }
      // If dependent value not found, return empty options
      return [];
    }
    // Otherwise use static options
    return optionsMetadata;
  }, [optionsMap, dependOn, data, optionsMetadata]);

  // Create mapping from value to label and vice versa
  const { valueToLabel, labelToValue, displayOptions } = useMemo(() => {
    if (!effectiveOptionsMetadata || effectiveOptionsMetadata.length === 0) {
      // No metadata, use values as-is
      return {
        valueToLabel: {},
        labelToValue: {},
        displayOptions: values,
      };
    }

    const valueToLabelMap: Record<string, string> = {};
    const labelToValueMap: Record<string, string> = {};
    const labels: string[] = [];

    effectiveOptionsMetadata.forEach((meta) => {
      valueToLabelMap[meta.value] = meta.label;
      labelToValueMap[meta.label] = meta.value;
      labels.push(meta.label);
    });

    return {
      valueToLabel: valueToLabelMap,
      labelToValue: labelToValueMap,
      displayOptions: labels,
    };
  }, [effectiveOptionsMetadata, values]);

  // Convert internal value to display label
  const displayValue = useMemo(() => {
    if (effectiveOptionsMetadata && effectiveOptionsMetadata.length > 0) {
      return valueToLabel[value] || value;
    }
    return value;
  }, [value, valueToLabel, effectiveOptionsMetadata]);

  // Handle selection change
  const handleChange = (selectedLabel: string) => {
    // Convert display label back to internal value
    if (effectiveOptionsMetadata && effectiveOptionsMetadata.length > 0) {
      const internalValue = labelToValue[selectedLabel] || selectedLabel;
      onValueChange(internalValue);
    } else {
      onValueChange(selectedLabel);
    }
  };

  return (
    <div
      style={{ width: eGridCell.clientWidth }}
      className="flex h-full items-center px-2"
    >
      <InputComponent
        setSelectedOption={handleChange}
        value={displayValue}
        options={displayOptions}
        password={false}
        placeholder={t("dropdown.selectOption")}
        id="apply-to-fields"
      />
    </div>
  );
}
