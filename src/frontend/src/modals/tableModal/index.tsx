import type { AgGridReact } from "ag-grid-react";
import { type ForwardedRef, forwardRef } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import TableComponent, {
  type TableComponentProps,
} from "@/components/core/parameterRenderComponent/components/tableComponent";
import type { TableOptionsTypeAPI } from "@/types/api";
import BaseModal from "../baseModal";

interface TableModalProps extends TableComponentProps {
  tableTitle: string;
  description: string;
  disabled?: boolean;
  children: React.ReactNode;
  tableOptions?: TableOptionsTypeAPI;
  hideColumns?: boolean | string[];
  tableIcon?: string;
  open?: boolean;
  setOpen?: (open: boolean) => void;
  onSave?: () => void;
  onCancel?: () => void;
  onActionButton?: (actionName: string) => void; // NEW: callback for action buttons
  actionButtonLoading?: string | null; // NEW: loading state for action buttons
}

const TableModal = forwardRef<AgGridReact, TableModalProps>(
  (
    {
      tableTitle,
      description,
      children,
      disabled,
      tableIcon,
      tableOptions, // Extract tableOptions explicitly
      open,
      setOpen,
      onSave,
      onCancel,
      onActionButton, // NEW: extract callback
      actionButtonLoading, // NEW: extract loading state
      ...props
    }: TableModalProps,
    ref: ForwardedRef<AgGridReact>,
  ) => {
    const { t } = useTranslation();

    const handleSetOpen = (newOpen: boolean) => {
      if (!newOpen && onCancel) {
        onCancel();
      }
      if (setOpen) {
        setOpen(newOpen);
      }
    };

    const handleOnEscapeKeyDown = (e: KeyboardEvent) => {
      const editingCells = (
        ref as React.RefObject<AgGridReact>
      )?.current?.api?.getEditingCells();

      if (editingCells && editingCells.length > 0) {
        e.preventDefault();
      }
    };

    return (
      <BaseModal
        onEscapeKeyDown={(e) => {
          handleOnEscapeKeyDown(e);
        }}
        disable={disabled}
        open={open}
        setOpen={(newOpen) => {
          handleSetOpen(newOpen);
        }}
      >
        <BaseModal.Trigger asChild>{children}</BaseModal.Trigger>
        <BaseModal.Header
          description={tableOptions?.description ?? description}
        >
          <span className="pr-2">{tableTitle}</span>
          <ForwardedIconComponent
            name={tableIcon ?? "Table"}
            className="mr-2 h-4 w-4"
          />
        </BaseModal.Header>
        <BaseModal.Content>
          <TableComponent
            className="h-full w-full"
            ref={ref}
            tableOptions={tableOptions}
            onActionButton={onActionButton}
            actionButtonLoading={actionButtonLoading}
            {...props}
          ></TableComponent>
        </BaseModal.Content>
        <BaseModal.Footer
          submit={
            onSave
              ? { label: t("components.button.save"), onClick: onSave }
              : undefined
          }
        ></BaseModal.Footer>
      </BaseModal>
    );
  },
);

export default TableModal;
