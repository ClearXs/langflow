import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useGetGlobalVariables,
  useGetSystemVariables,
} from '@/controllers/API/queries/variables';
import GeneralDeleteConfirmationModal from '@/shared/components/delete-confirmation-modal';
import { cn } from '../../../../../utils/utils';
import ForwardedIconComponent from '../../../../common/genericIconComponent';
import { CommandItem } from '../../../../ui/command';
import GlobalVariableModal from '../../../GlobalVariableModal/GlobalVariableModal';
import { getPlaceholder } from '../../helpers/get-placeholder-disabled';
import type { InputGlobalComponentType, InputProps } from '../../types';
import InputComponent from '../inputComponent';
import { useInitialLoad, useUnavailableField } from './hooks';
import type { GlobalVariable, GlobalVariableHandlers } from './types';

export default function InputGlobalComponent({
  display_name,
  disabled,
  handleOnNewValue,
  value,
  id,
  load_from_db,
  password,
  allowCustomValue = true,
  editNode = false,
  placeholder,
  isToolMode = false,
  hasRefreshButton = false,
}: InputProps<string, InputGlobalComponentType>): JSX.Element {
  const { data: globalVariables } = useGetGlobalVariables();
  const { data: systemVariables } = useGetSystemVariables();

  const { t } = useTranslation();

  // Local state for immediate UI feedback (0ms input delay)
  const [localValue, setLocalValue] = useState(value ?? '');

  // Sync prop changes to local state
  useEffect(() => {
    setLocalValue(value ?? '');
  }, [value]);

  // Merge global and system variables with type labels
  const allVariables = useMemo(() => {
    const global = (globalVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.globalTag')}]`,
      originalName: v.name,
      isSystem: false,
    }));

    const system = (systemVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.systemTag')}]`,
      originalName: v.name,
      isSystem: true,
    }));

    return [...global, ...system];
  }, [globalVariables, systemVariables, t]);

  // // Safely cast the data to our typed interface
  const typedGlobalVariables: GlobalVariable[] = globalVariables ?? [];
  const currentValue = localValue; // Use local value instead of prop value
  const isDisabled = disabled ?? false;
  const loadFromDb = load_from_db ?? false;

  // Check if value exists in either global or system variables
  const valueExists = useMemo(() => {
    return allVariables.some((v) => v.originalName === currentValue);
  }, [allVariables, currentValue]);

  const unavailableField = useUnavailableField(display_name, currentValue);

  // For initial load, only check global variables (not system variables)
  // System variables don't need database loading
  const valueExistsInGlobalOnly = useMemo(() => {
    return typedGlobalVariables.some((v) => v.name === currentValue);
  }, [typedGlobalVariables, currentValue]);

  useInitialLoad(
    isDisabled,
    loadFromDb,
    typedGlobalVariables,
    valueExistsInGlobalOnly, // Use global-only check for initial load
    unavailableField,
    handleOnNewValue,
    currentValue // Pass current value to prevent clearing valid selections
  );

  // Clean up when selected variable no longer exists
  // Only clear if it's supposed to be from DB and doesn't exist in either global or system
  useEffect(() => {
    if (loadFromDb && currentValue && !valueExists && !isDisabled) {
      handleOnNewValue(
        { value: '', load_from_db: false },
        { skipSnapshot: true }
      );
    }
  }, [loadFromDb, currentValue, valueExists, isDisabled, handleOnNewValue]);

  // Create handlers object for better organization
  const handlers: GlobalVariableHandlers = {
    // Handler for deleting global variables
    handleVariableDelete: (variableName: string) => {
      if (value === variableName) {
        handleOnNewValue({
          value: '',
          load_from_db: false,
        });
      }
    },

    // Handler for selecting a global variable or system variable
    handleVariableSelect: (selectedDisplayName: string) => {
      // Find the variable by display name
      const selected = allVariables.find(
        (v) => v.displayName === selectedDisplayName
      );

      if (selected) {
        // Insert variable reference into current value
        // Use {variableName} format for template substitution
        const variableRef = `{${selected.originalName}}`;
        const newValue = currentValue
          ? `${currentValue} ${variableRef}`
          : variableRef;

        // Update with load_from_db: false to keep input editable
        // The backend will still resolve {variableName} patterns
        handleOnNewValue({
          value: newValue,
          load_from_db: false,
        });
      }
    },

    // Handler for input changes
    handleInputChange: (inputValue: string, skipSnapshot?: boolean) => {
      // Update local state immediately for 0ms input feedback
      setLocalValue(inputValue);

      // Still trigger debounced store update
      handleOnNewValue(
        { value: inputValue, load_from_db: false },
        { skipSnapshot }
      );
    },
  };

  // Render add new variable button
  const renderAddVariableButton = () => {
    const { t } = useTranslation();
    return (
      <GlobalVariableModal referenceField={display_name} disabled={disabled}>
        <CommandItem value='doNotFilter-addNewVariable'>
          <ForwardedIconComponent
            name='Plus'
            className={cn('mr-2 h-4 w-4 text-primary')}
            aria-hidden='true'
          />
          <span>{t('components.button.addNewVariable')}</span>
        </CommandItem>
      </GlobalVariableModal>
    );
  };

  // Render delete button for each option (only for global variables, not system variables)
  const renderDeleteButton = (option: string) => {
    // Check if this is a global variable (contains globalTag)
    const isGlobalVariable = option.includes(`[${t('variable.globalTag')}]`);

    if (!isGlobalVariable) {
      // Don't show delete button for system variables
      return null;
    }

    // Extract the original name from display name for deletion
    const variable = allVariables.find((v) => v.displayName === option);
    if (!variable || variable.isSystem) return null;

    return (
      <GeneralDeleteConfirmationModal
        option={variable.originalName}
        onConfirmDelete={() =>
          handlers.handleVariableDelete(variable.originalName)
        }
      />
    );
  };

  // Extract options list with display names
  const variableOptions = allVariables.map((v) => v.displayName);

  // Don't use selectedOption - keep input always editable
  // Variables are inserted as {variableName} in the text
  const selectedOption = '';

  return (
    <InputComponent
      nodeStyle
      popoverWidth='17.5rem'
      placeholder={getPlaceholder(disabled, placeholder)}
      id={id}
      editNode={editNode}
      disabled={disabled}
      password={password ?? false}
      value={currentValue}
      options={variableOptions}
      optionsPlaceholder={t('variable.variableList')}
      optionsIcon='Variable'
      optionsButton={renderAddVariableButton()}
      optionButton={renderDeleteButton}
      selectedOption={selectedOption}
      setSelectedOption={handlers.handleVariableSelect}
      onChange={handlers.handleInputChange}
      allowCustomValue={allowCustomValue}
      isToolMode={isToolMode}
      hasRefreshButton={hasRefreshButton}
    />
  );
}
