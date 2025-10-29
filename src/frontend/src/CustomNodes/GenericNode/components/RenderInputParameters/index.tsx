import { useMemo } from "react";
import { getNodeInputColors } from "@/CustomNodes/helpers/get-node-input-colors";
import { getNodeInputColorsName } from "@/CustomNodes/helpers/get-node-input-colors-name";
import { sortToolModeFields } from "@/CustomNodes/helpers/sort-tool-mode-field";
import getFieldTitle from "@/CustomNodes/utils/get-field-title";
import { scapedJSONStringfy } from "@/utils/reactflowUtils";
import NodeInputField from "../NodeInputField";

const RenderInputParameters = ({
  data,
  types,
  isToolMode,
  showNode,
  shownOutputs,
  showHiddenOutputs,
}) => {
  const templateFields = useMemo(() => {
    return Object.keys(data.node?.template || {})
      .filter((templateField) => templateField.charAt(0) !== "_")
      .sort((a, b) =>
        sortToolModeFields(
          a,
          b,
          data.node!.template,
          data.node?.field_order ?? [],
          isToolMode,
        ),
      );
  }, [data.node?.template, data.node?.field_order, isToolMode]);

  const shownTemplateFields = useMemo(() => {
    // Only show code field for custom components (CustomComponent or custom_components)
    const isCustomComponent =
      data?.type === "CustomComponent" || data?.type === "custom_components";

    return templateFields.filter((templateField) => {
      const template = data.node?.template[templateField];

      // Filter out code field for built-in components to improve performance
      if (
        !isCustomComponent &&
        templateField === "code" &&
        template?.type === "code"
      ) {
        return false;
      }

      return (
        template?.show &&
        !template?.advanced &&
        !(template?.tool_mode && isToolMode)
      );
    });
  }, [templateFields, data.node?.template, data?.type, isToolMode]);

  const memoizedColors = useMemo(() => {
    const colorMap = new Map();

    templateFields.forEach((templateField) => {
      const template = data.node?.template[templateField];
      if (template) {
        colorMap.set(templateField, {
          colors: getNodeInputColors(
            template.input_types,
            template.type,
            types,
          ),
          colorsName: getNodeInputColorsName(
            template.input_types,
            template.type,
            types,
          ),
        });
      }
    });

    return colorMap;
  }, [templateFields, types, data.node?.template]);

  const memoizedKeys = useMemo(() => {
    const keyMap = new Map();

    templateFields.forEach((templateField) => {
      const template = data.node?.template[templateField];
      if (template) {
        keyMap.set(
          templateField,
          scapedJSONStringfy({
            inputTypes: template.input_types,
            type: template.type,
            id: data.id,
            fieldName: templateField,
            proxy: template.proxy,
          }),
        );
      }
    });

    return keyMap;
  }, [templateFields, data.id, data.node?.template]);

  const renderInputParameter = shownTemplateFields.map(
    (templateField: string, idx: number) => {
      const template = data.node?.template[templateField];

      const memoizedColor = memoizedColors.get(templateField);
      const memoizedKey = memoizedKeys.get(templateField);

      return (
        <NodeInputField
          lastInput={
            !(shownOutputs.length > 0 || showHiddenOutputs) &&
            idx === shownTemplateFields.length - 1
          }
          key={memoizedKey}
          data={data}
          colors={memoizedColor.colors}
          title={getFieldTitle(data.node?.template!, templateField)}
          info={template.info!}
          name={templateField}
          tooltipTitle={template.input_types?.join("\n") ?? template.type}
          required={template.required}
          id={{
            inputTypes: template.input_types,
            type: template.type,
            id: data.id,
            fieldName: templateField,
          }}
          type={template.type}
          optionalHandle={template.input_types}
          proxy={template.proxy}
          showNode={showNode}
          colorName={memoizedColor.colorsName}
          isToolMode={isToolMode && template.tool_mode}
        />
      );
    },
  );

  return <>{renderInputParameter}</>;
};

export default RenderInputParameters;
