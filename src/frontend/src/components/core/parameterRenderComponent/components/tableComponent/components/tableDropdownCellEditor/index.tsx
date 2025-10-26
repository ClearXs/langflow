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
  onValueChange,
  colDef,
  eGridCell,
}: CustomCellEditorProps & {
  values: string[];
  optionsMetadata?: OptionMetadata[];
}) {
  const { t } = useTranslation();
  // Create mapping from value to label and vice versa
  const { valueToLabel, labelToValue, displayOptions } = useMemo(() => {
    if (!optionsMetadata || optionsMetadata.length === 0) {
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

    optionsMetadata.forEach((meta) => {
      valueToLabelMap[meta.value] = meta.label;
      labelToValueMap[meta.label] = meta.value;
      labels.push(meta.label);
    });

    return {
      valueToLabel: valueToLabelMap,
      labelToValue: labelToValueMap,
      displayOptions: labels,
    };
  }, [optionsMetadata, values]);

  // Convert internal value to display label
  const displayValue = useMemo(() => {
    if (optionsMetadata && optionsMetadata.length > 0) {
      return valueToLabel[value] || value;
    }
    return value;
  }, [value, valueToLabel, optionsMetadata]);

  // Handle selection change
  const handleChange = (selectedLabel: string) => {
    // Convert display label back to internal value
    if (optionsMetadata && optionsMetadata.length > 0) {
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
