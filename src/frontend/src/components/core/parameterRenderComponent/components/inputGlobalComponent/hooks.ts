import { useCallback, useEffect, useMemo, useRef } from "react";
import { useGlobalVariablesStore } from "@/stores/globalVariablesStore/globalVariables";
import type { GlobalVariable } from "./types";

// Custom hook for managing global variable value existence
export const useGlobalVariableValue = (
  value: string,
  globalVariables: GlobalVariable[],
) => {
  return useMemo(() => {
    return (
      globalVariables?.some((variable) => variable.name === value) ?? false
    );
  }, [globalVariables, value]);
};

// Custom hook for managing unavailable fields
export const useUnavailableField = (
  displayName: string | undefined,
  value: string,
) => {
  const unavailableFields = useGlobalVariablesStore(
    (state) => state.unavailableFields,
  );

  return useMemo(() => {
    if (
      displayName &&
      unavailableFields &&
      Object.keys(unavailableFields).includes(displayName) &&
      value === ""
    ) {
      return unavailableFields[displayName];
    }
    return null;
  }, [unavailableFields, displayName, value]);
};

// Custom hook for handling initial load logic
export const useInitialLoad = (
  disabled: boolean,
  loadFromDb: boolean,
  globalVariables: GlobalVariable[],
  valueExists: boolean,
  unavailableField: string | null,
  handleOnNewValue: (
    value: { value: string; load_from_db: boolean },
    options?: { skipSnapshot: boolean },
  ) => void,
  currentValue: string,
) => {
  const initialLoadCompleted = useRef(false);
  const initialCheckCompleted = useRef(false);
  const handleOnNewValueRef = useRef(handleOnNewValue);

  // Keep the latest handleOnNewValue reference
  handleOnNewValueRef.current = handleOnNewValue;

  // Handle database loading when value doesn't exist
  // This effect is for INITIAL LOAD only - runs once when component mounts
  // It should NOT trigger when user actively selects a new variable
  useEffect(() => {
    // Only run this check once on initial load
    if (initialCheckCompleted.current) {
      return;
    }

    // Skip if disabled
    if (disabled) {
      return;
    }

    // Skip if loadFromDb is false (no database variable selected)
    if (!loadFromDb) {
      initialCheckCompleted.current = true;
      return;
    }

    // Skip if no global variables loaded yet (wait for data)
    if (!globalVariables.length) {
      return;
    }

    // Mark as completed - we have all the data we need
    initialCheckCompleted.current = true;

    // If the value exists, don't clear it
    if (valueExists) {
      return;
    }

    // If there's a current value, don't clear it
    if (currentValue) {
      return;
    }

    // At this point: loadFromDb is true, value doesn't exist, and currentValue is empty
    // This scenario only happens on initial load with an invalid reference
    handleOnNewValueRef.current(
      { value: "", load_from_db: false },
      { skipSnapshot: true },
    );
  }, [disabled, loadFromDb, globalVariables.length, valueExists, currentValue]);

  // Handle unavailable field initialization
  useEffect(() => {
    if (initialLoadCompleted.current || disabled || unavailableField === null) {
      return;
    }

    handleOnNewValueRef.current(
      { value: unavailableField, load_from_db: true },
      { skipSnapshot: true },
    );

    initialLoadCompleted.current = true;
  }, [unavailableField, disabled]);
};
