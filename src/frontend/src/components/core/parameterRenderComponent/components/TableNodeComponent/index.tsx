import type {
  DataTypeDefinition,
  SelectionChangedEvent,
} from "ag-grid-community";
import type { AgGridReact } from "ag-grid-react";
import { cloneDeep } from "lodash";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { mutateTemplate } from "@/CustomNodes/helpers/mutate-template";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { previewUpstreamData } from "@/controllers/API/datasources";
import { usePostTemplateValue } from "@/controllers/API/queries/nodes/use-post-template-value";
import TableModal from "@/modals/tableModal";
import useAlertStore from "@/stores/alertStore";
import useFlowStore from "@/stores/flowStore";
import { isMarkdownTable } from "@/utils/markdownUtils";
import { FormatColumns, generateBackendColumnsFromValue } from "@/utils/utils";
import { ForwardedIconComponent } from "../../../../common/genericIconComponent";
import { Button } from "../../../../ui/button";
import type { InputProps, TableComponentType } from "../../types";

export default function TableNodeComponent({
  tableTitle,
  description,
  value,
  editNode = false,
  id = "",
  columns,
  handleOnNewValue,
  disabled = false,
  table_options,
  trigger_icon = "Table",
  table_icon,
  componentName,
  ...props
}: InputProps<any[], TableComponentType> & {
  componentName?: string;
}): JSX.Element {
  const { t } = useTranslation();

  const {
    trigger_text = t("components.table.openTable"),
    nodeId,
    nodeClass,
    handleNodeClass,
  } = props;

  // API hooks for action button triggers
  const postTemplateValue = usePostTemplateValue({
    parameterId: id,
    nodeId: nodeId,
    node: nodeClass,
  });
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const dataTypeDefinitions: {
    [cellDataType: string]: DataTypeDefinition<any>;
  } = useMemo(() => {
    return {
      // override `date` to handle custom date format `dd/mm/yyyy`
      date: {
        baseDataType: "date",
        extendsDataType: "date",
        valueParser: (params) => {
          if (params.newValue == null) {
            return null;
          }
          // convert from `dd/mm/yyyy`
          const dateParts = params.newValue.split("/");
          return dateParts.length === 3
            ? new Date(
                parseInt(dateParts[2]),
                parseInt(dateParts[1]) - 1,
                parseInt(dateParts[0]),
              )
            : null;
        },
        valueFormatter: (params) => {
          let date = params.value;
          if (typeof params.value === "string") {
            date = new Date(params.value);
          }
          // convert to `dd/mm/yyyy`
          return date == null
            ? "‎"
            : `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
        },
      },
      number: {
        baseDataType: "number",
        extendsDataType: "number",
        valueFormatter: (params) =>
          params.value == null ? "‎" : `${params.value}`,
      },
    };
  }, []);
  const [selectedNodes, setSelectedNodes] = useState<Array<any>>([]);
  const [tempValue, setTempValue] = useState<any[]>(cloneDeep(value));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const agGrid = useRef<AgGridReact>(null);
  // Add useEffect to sync with incoming value changes
  useEffect(() => {
    setTempValue(cloneDeep(value));
  }, [value]);

  const componentColumns = columns
    ? columns
    : generateBackendColumnsFromValue(tempValue ?? [], table_options);
  let AgColumns = FormatColumns(componentColumns);
  // add info to each column
  AgColumns = AgColumns.map((col) => {
    if (col.context?.info) {
      return {
        ...col,
        headerComponent: () => (
          <div className="flex items-center gap-1">
            <div>{col.headerName}</div>
            <ShadTooltip content={col.context?.info}>
              <div>
                <ForwardedIconComponent name="Info" className="h-4 w-4" />
              </div>
            </ShadTooltip>
          </div>
        ),
      };
    }
    return col;
  });
  function setAllRows() {
    if (agGrid.current && !agGrid.current.api.isDestroyed()) {
      const rows: any = [];
      agGrid.current.api.forEachNode((node) => rows.push(node.data));
      setTempValue(rows);
    }
  }
  function deleteRow() {
    if (agGrid.current && selectedNodes.length > 0) {
      agGrid.current.api.applyTransaction({
        remove: selectedNodes.map((node) => node.data),
      });
      setSelectedNodes([]);
      setAllRows();
    }
  }
  function duplicateRow() {
    if (agGrid.current && selectedNodes.length > 0) {
      const toDuplicate = selectedNodes.map((node) => cloneDeep(node.data));
      setSelectedNodes([]);
      setTempValue([...tempValue, ...toDuplicate]);
    }
  }
  function addRow() {
    const newRow = {};
    componentColumns.forEach((column) => {
      newRow[column.name] = column.default ?? null; // Use the default value if available
    });
    setTempValue([...tempValue, newRow]);
  }

  // Handle action button clicks
  async function handleActionButton(actionName: string) {
    if (!nodeId || !nodeClass || !handleNodeClass) {
      return;
    }

    try {
      // Check if this action requires preview upstream data
      const actionButton = table_options?.action_buttons?.find(
        (btn) => btn.name === actionName,
      );
      const previewConfig = actionButton?.preview_upstream;

      // If preview_upstream is configured and enabled, fetch upstream data first
      if (previewConfig?.enabled) {
        const currentFlowId = useFlowStore.getState().currentFlowId;
        if (!currentFlowId) {
          setErrorData({
            title: t("errors.flowNotFound"),
            list: [t("errors.saveFlowFirst")],
          });
          return;
        }

        const previewResponse = await previewUpstreamData(
          currentFlowId,
          nodeId,
          {
            input_name: previewConfig.input_name,
            sample_size: previewConfig.sample_size || 10,
          },
        );

        if (!previewResponse.success) {
          setErrorData({
            title: t("errors.previewFailed"),
            list: [previewResponse.error || t("errors.unknownError")],
          });
          return;
        }

        // Transform field data using custom transform function if provided
        // Otherwise use default transformation (field_name -> field_name)
        let transformedData;
        if (previewConfig.transform) {
          transformedData = previewConfig.transform(previewResponse.fields);
        } else {
          transformedData = previewResponse.fields.map((field) => ({
            source_field: field.field_name,
            target_field: field.field_name,
            description: "",
          }));
        }

        // Call mutateTemplate with transformed data
        await mutateTemplate(
          transformedData,
          nodeId,
          nodeClass,
          handleNodeClass,
          postTemplateValue,
          setErrorData,
          componentName || id,
          undefined,
          undefined,
          actionName,
        );
      } else {
        // No preview needed - use original behavior
        await mutateTemplate(
          actionName,
          nodeId,
          nodeClass,
          handleNodeClass,
          postTemplateValue,
          setErrorData,
          componentName || id,
          undefined,
          undefined,
          actionName,
        );
      }
    } catch (error) {
      setErrorData({
        title: t("errors.actionFailed"),
        list: [
          error instanceof Error ? error.message : t("errors.unknownError"),
        ],
      });
    }
  }

  function updateComponent() {
    setAllRows();
  }

  function handleSave() {
    handleOnNewValue({ value: tempValue });
    setIsModalOpen(false);
  }

  function handleCancel() {
    setTempValue(cloneDeep(value));
    setIsModalOpen(false);
  }

  const editable = componentColumns
    .map((column) => {
      const isCustomEdit =
        column.formatter &&
        ((column.formatter === "text" && column.edit_mode === "modal") ||
          column.formatter === "json");
      return {
        field: column.name,
        onUpdate: updateComponent,
        editableCell: isCustomEdit ? false : true,
      };
    })
    .filter(
      (col) =>
        columns?.find((c) => c.name === col.field)?.disable_edit !== true,
    );

  function parseTSVorMarkdownTable(clipboard: string, columns: any[]) {
    if (!clipboard.trim()) return [];

    // Try TSV (Excel/Sheets)
    if (clipboard.includes("\t")) {
      const lines = clipboard.trim().split(/\r?\n/);
      // More robust header detection - check if first line contains column names
      const firstLineCells = lines[0].split("\t");
      const hasHeader = firstLineCells.some((cell) =>
        columns.some((col) => col.name === cell.trim()),
      );
      const dataLines = hasHeader ? lines.slice(1) : lines;

      return dataLines.map((line) => {
        const cells = line.split("\t");
        if (cells.length > columns.length) {
          // Truncate extra cells
          cells.length = columns.length;
        }
        const row = {};
        columns.forEach((col, i) => {
          row[col.name] = cells[i]?.trim() ?? null;
        });
        return row;
      });
    }

    // Try markdown table
    if (isMarkdownTable(clipboard)) {
      const lines = clipboard
        .trim()
        .split(/\r?\n/)
        .filter((l) => l.includes("|"));
      if (lines.length < 2) return [];

      // Validate that second line is a separator (contains dashes)
      if (lines.length > 1 && !lines[1].includes("-")) {
        // No separator found, treat all lines as data
        const dataLines = lines;
        return dataLines.map((line) => {
          const cells = line
            .split("|")
            .slice(1, -1)
            .map((c) => c.trim());
          const row = {};
          columns.forEach((col, i) => {
            row[col.name] = cells[i] ?? null;
          });
          return row;
        });
      }

      // Assume first line is header, second is separator
      const dataLines = lines.slice(2);
      return dataLines.map((line) => {
        const cells = line
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        const row = {};
        columns.forEach((col, i) => {
          row[col.name] = cells[i] ?? null;
        });
        return row;
      });
    }
    return [];
  }

  return (
    <div
      className={
        "flex w-full items-center" + (disabled ? " cursor-not-allowed" : "")
      }
      onPaste={(e) => {
        if (!isModalOpen) return;
        try {
          const clipboard = e.clipboardData.getData("text");
          const rows = parseTSVorMarkdownTable(clipboard, componentColumns);
          if (rows.length > 0) {
            setTempValue((prev) => [...prev, ...rows]);
            e.preventDefault();
            // Consider adding a toast notification here:
            // toast.success(`Imported ${rows.length} rows successfully`);
          } else {
            // Consider adding a toast notification for failed parsing:
            // toast.error("Could not parse clipboard data as table format");
          }
        } catch (error) {
          console.error("Error parsing clipboard data:", error);
          // Consider adding a toast notification for errors:
          // toast.error("Error importing clipboard data");
        }
      }}
    >
      <div className="flex w-full items-center gap-3" data-testid={"div-" + id}>
        <TableModal
          open={isModalOpen}
          setOpen={setIsModalOpen}
          stopEditingWhenCellsLoseFocus={true}
          tableIcon={table_icon}
          tableOptions={table_options}
          dataTypeDefinitions={dataTypeDefinitions}
          autoSizeStrategy={{ type: "fitGridWidth", defaultMinWidth: 100 }}
          tableTitle={tableTitle}
          description={description}
          ref={agGrid}
          onSelectionChanged={(event: SelectionChangedEvent) => {
            setSelectedNodes(event.api.getSelectedNodes());
          }}
          rowSelection={table_options?.block_select ? undefined : "multiple"}
          editable={editable}
          pagination={table_options?.pagination ?? !table_options?.hide_options}
          addRow={addRow}
          onDelete={deleteRow}
          onActionButton={handleActionButton}
          gridOptions={{
            ensureDomOrder: true,
            suppressRowClickSelection: true,
          }}
          onDuplicate={duplicateRow}
          displayEmptyAlert={false}
          className="h-full w-full"
          columnDefs={AgColumns}
          rowData={tempValue}
          context={{ field_parsers: table_options?.field_parsers }}
          onSave={handleSave}
          onCancel={handleCancel}
        >
          <Button
            disabled={disabled}
            variant="primary"
            size={editNode ? "xs" : "default"}
            className={
              "w-full " +
              (disabled ? "pointer-events-none cursor-not-allowed" : "")
            }
          >
            <ForwardedIconComponent
              name={trigger_icon}
              className="mt-px h-4 w-4"
            />
            <span className="font-normal">{trigger_text}</span>
          </Button>
        </TableModal>
      </div>
    </div>
  );
}
