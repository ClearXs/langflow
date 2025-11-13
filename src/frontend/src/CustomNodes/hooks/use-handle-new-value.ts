import { useUpdateNodeInternals } from "@xyflow/react";
import { cloneDeep, debounce } from "lodash";
import { useCallback, useMemo, useRef } from "react";
import { DEBOUNCE_FIELD_LIST } from "@/constants/constants";
import { usePostTemplateValue } from "@/controllers/API/queries/nodes/use-post-template-value";
import { track } from "@/customization/utils/analytics";
import useAlertStore from "@/stores/alertStore";
import useFlowStore from "@/stores/flowStore";
import useFlowsManagerStore from "@/stores/flowsManagerStore";
import type { APIClassType, InputFieldType } from "@/types/api";
import type { AllNodeType } from "@/types/flow";
import { mutateTemplate } from "../helpers/mutate-template";

const DEBOUNCE_TIME_1_SECOND = 1000;

/**
 * Check if only the value of a parameter changed (not its structure)
 * This helps optimize updateNodeInternals calls - we only need to update
 * React Flow internals when the node structure changes (handles, connections),
 * not when just values change.
 */
const hasOnlyValueChanged = (
  oldNode: APIClassType,
  newNode: APIClassType,
): boolean => {
  const oldTemplate = oldNode.template;
  const newTemplate = newNode.template;

  if (!oldTemplate || !newTemplate) return false;

  const oldKeys = Object.keys(oldTemplate);
  const newKeys = Object.keys(newTemplate);

  // If number of fields changed, structure changed
  if (oldKeys.length !== newKeys.length) return false;

  // Check each field's structure (excluding value)
  for (const key of oldKeys) {
    const oldField = oldTemplate[key];
    const newField = newTemplate[key];

    if (!newField) return false;

    // Compare structural properties (not value)
    const structuralProps = [
      "field_type",
      "input_types",
      "required",
      "show",
      "advanced",
      "list",
      "display_name",
      "options", // dropdown options change = structure change
    ];

    for (const prop of structuralProps) {
      // Use JSON.stringify for deep comparison of arrays/objects
      if (JSON.stringify(oldField[prop]) !== JSON.stringify(newField[prop])) {
        return false; // Structure changed
      }
    }
  }

  return true; // Only values changed
};

export type handleOnNewValueType = (
  changes: Partial<InputFieldType>,
  options?: {
    skipSnapshot?: boolean;
    setNodeClass?: (node: APIClassType) => void;
  },
) => void;

const useHandleOnNewValue = ({
  node,
  nodeId,
  name,
  setNode: setNodeExternal,
}: {
  node: APIClassType;
  nodeId: string;
  name: string;
  setNode?: (
    id: string,
    update: AllNodeType | ((oldState: AllNodeType) => AllNodeType),
  ) => void;
}) => {
  const takeSnapshot = useFlowsManagerStore((state) => state.takeSnapshot);
  const setNode = setNodeExternal ?? useFlowStore((state) => state.setNode);
  const getNode = useFlowStore((state) => state.getNode); // Add getNode to fetch old node
  const updateNodeInternals = useUpdateNodeInternals();
  const setErrorData = useAlertStore((state) => state.setErrorData);

  // Memoize the postTemplateValue hook to prevent unnecessary re-renders
  const postTemplateValue = usePostTemplateValue(
    useMemo(
      () => ({
        parameterId: name,
        nodeId,
        node,
        tool_mode: node.tool_mode ?? false,
      }),
      [name, nodeId, node, node.tool_mode],
    ),
  );

  // Memoize the node update function
  const updateNodeState = useCallback(
    (newNode: APIClassType, oldNode?: APIClassType) => {
      // Performance: Check if only values changed (not structure)
      // Only call updateNodeInternals when structure changes (handles, connections, etc.)
      const onlyValueChanged = oldNode && hasOnlyValueChanged(oldNode, newNode);

      setNode(
        nodeId,
        (oldNodeData) => {
          // Performance: Use shallow copy instead of cloneDeep for better performance
          // Only the node property needs to be updated, other data properties can be reused
          return {
            ...oldNodeData,
            data: {
              ...oldNodeData.data,
              node: newNode,
            },
          };
        },
        true,
        () => {
          // OPTIMIZATION: Only update React Flow internals when structure changes
          // This significantly improves performance by avoiding expensive layout recalculations
          // on every keystroke
          if (!onlyValueChanged) {
            updateNodeInternals(nodeId);
          }
        },
      );
    },
    [nodeId, setNode, updateNodeInternals],
  );

  const debouncedMutateRef = useRef<any>(null);
  const debouncedSnapshotRef = useRef<any>(null);
  const debouncedUpdateStateRef = useRef<any>(null);

  const handleOnNewValue: handleOnNewValueType = useCallback(
    async (changes, options?) => {
      // Performance: Use shallow copy with structural sharing instead of cloneDeep
      // Only clone the template and the specific parameter being changed
      const newNode = {
        ...node,
        template: {
          ...node.template,
          [name]: {
            ...node.template[name],
          },
        },
      };
      const template = newNode.template;

      // Debounced tracking
      track("Component Edited", { nodeId });

      if (nodeId.toLowerCase().includes("astra") && name === "database_name") {
        track("Database Selected", { nodeId, databaseName: changes.value });
      }

      if (!template) {
        setErrorData({ title: "Template not found in the component" });
        return;
      }

      const parameter = template[name];

      if (!parameter) {
        setErrorData({ title: "Parameter not found in the template" });
        return;
      }

      const shouldDebounce = DEBOUNCE_FIELD_LIST.includes(
        parameter?._input_type,
      );

      // Use debounced snapshot to avoid freezing UI on every keystroke
      if (!options?.skipSnapshot) {
        if (!debouncedSnapshotRef.current) {
          debouncedSnapshotRef.current = debounce(takeSnapshot, 500);
        }
        debouncedSnapshotRef.current();
      }

      Object.entries(changes).forEach(([key, value]) => {
        if (value !== undefined) parameter[key] = value;
      });

      // Check if this is a simple text field that doesn't need backend validation
      const isSimpleTextField =
        (parameter.field_type === "str" ||
          parameter._input_type === "MessageTextInput" ||
          parameter._input_type === "MultilineInput" ||
          parameter._input_type === "TextInput") &&
        !parameter.options && // No dropdown options
        !parameter.dynamic && // Not a dynamic field
        !parameter.refresh_button; // No refresh button

      const shouldUpdate = parameter.real_time_refresh && !isSimpleTextField;

      const setNodeClass = (newNodeClass: APIClassType) => {
        options?.setNodeClass?.(newNodeClass);
        // Get old node for comparison
        const oldFlowNode = getNode(nodeId);
        const oldNode = oldFlowNode?.data?.node;
        updateNodeState(newNodeClass, oldNode);
      };

      if (shouldUpdate && changes.value !== undefined) {
        if (!debouncedMutateRef.current) {
          debouncedMutateRef.current = debounce(
            async (
              value,
              node,
              setNodeClassFn,
              postTemplateFn,
              setErrorDataFn,
            ) => {
              await mutateTemplate(
                value,
                nodeId,
                node,
                setNodeClassFn,
                postTemplateFn,
                setErrorDataFn,
              );
            },
            shouldDebounce ? DEBOUNCE_TIME_1_SECOND : 0,
          );
        }
        debouncedMutateRef.current(
          changes.value,
          newNode,
          setNodeClass,
          postTemplateValue,
          setErrorData,
        );
      }

      // CRITICAL FIX: Debounce the state update to prevent UI freezing
      // This is the main cause of input lag - every keystroke was triggering immediate store update
      if (!debouncedUpdateStateRef.current) {
        debouncedUpdateStateRef.current = debounce(
          (newNode, oldNode) => updateNodeState(newNode, oldNode),
          150, // Restored to 150ms - combined with local state pattern for immediate UI feedback
        );
      }

      // Get old node for comparison before update
      const oldFlowNode = getNode(nodeId);
      const oldNode = oldFlowNode?.data?.node;
      debouncedUpdateStateRef.current(newNode, oldNode);
    },
    [
      node,
      nodeId,
      name,
      takeSnapshot,
      postTemplateValue,
      setErrorData,
      updateNodeState,
      getNode, // Add getNode to dependencies
    ],
  );

  return { handleOnNewValue };
};

export default useHandleOnNewValue;
