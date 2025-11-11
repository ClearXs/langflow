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
    (newNode: APIClassType) => {
      setNode(
        nodeId,
        (oldNode) => {
          // Performance: Use shallow copy instead of cloneDeep for better performance
          // Only the node property needs to be updated, other data properties can be reused
          return {
            ...oldNode,
            data: {
              ...oldNode.data,
              node: newNode,
            },
          };
        },
        true,
        () => {
          updateNodeInternals(nodeId);
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
        updateNodeState(newNodeClass);
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
          (node) => updateNodeState(node),
          150, // Restored to 150ms - combined with local state pattern for immediate UI feedback
        );
      }
      debouncedUpdateStateRef.current(newNode);
    },
    [
      node,
      nodeId,
      name,
      takeSnapshot,
      postTemplateValue,
      setErrorData,
      updateNodeState,
    ],
  );

  return { handleOnNewValue };
};

export default useHandleOnNewValue;
