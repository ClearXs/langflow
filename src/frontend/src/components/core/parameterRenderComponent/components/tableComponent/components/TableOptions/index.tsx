import { useTranslation } from "react-i18next";
import IconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import type { TableOptionsTypeAPI } from "@/types/api";
import { cn } from "@/utils/utils";

export default function TableOptions({
  resetGrid,
  duplicateRow,
  deleteRow,
  hasSelection,
  stateChange,
  paginationInfo,
  addRow,
  tableOptions,
  onActionButton,
}: {
  resetGrid: () => void;
  duplicateRow?: () => void;
  deleteRow?: () => void;
  addRow?: () => void;
  hasSelection: boolean;
  stateChange: boolean;
  tableOptions?: TableOptionsTypeAPI;
  paginationInfo?: string;
  onActionButton?: (actionName: string) => void;
}): JSX.Element {
  const { t } = useTranslation();

  // Filter action buttons by position
  const topButtons =
    tableOptions?.action_buttons?.filter((btn) => btn.position === "top") || [];

  return (
    <div className={cn("absolute bottom-3 left-6")}>
      <div className="flex items-center gap-3">
        {/* Top Action Buttons */}
        {topButtons.map((button) => (
          <div key={button.name}>
            <ShadTooltip content={button.label}>
              <Button
                data-testid={`action-button-${button.name}`}
                unstyled
                onClick={() => onActionButton?.(button.name)}
              >
                <IconComponent
                  name={button.icon}
                  className={cn("h-5 w-5 text-primary transition-all")}
                />
              </Button>
            </ShadTooltip>
          </div>
        ))}
        {addRow && !tableOptions?.block_add && (
          <div>
            <ShadTooltip content={t("table.options.addRow")}>
              <Button data-testid="add-row-button" unstyled onClick={addRow}>
                <IconComponent
                  name="Plus"
                  className={cn("h-5 w-5 text-primary transition-all")}
                />
              </Button>
            </ShadTooltip>
          </div>
        )}
        {duplicateRow && (
          <div>
            <ShadTooltip
              content={
                !hasSelection ? (
                  <span>{t("table.options.selectToDuplicate")}</span>
                ) : (
                  <span>{t("table.options.duplicateSelected")}</span>
                )
              }
            >
              <Button
                data-testid="duplicate-row-button"
                unstyled
                onClick={duplicateRow}
                disabled={!hasSelection}
              >
                <IconComponent
                  name="Copy"
                  className={cn(
                    "h-5 w-5 transition-all",
                    hasSelection
                      ? "text-primary"
                      : "cursor-not-allowed text-placeholder-foreground",
                  )}
                />
              </Button>
            </ShadTooltip>
          </div>
        )}
        {deleteRow && (
          <div>
            <ShadTooltip
              content={
                !hasSelection ? (
                  <span>{t("table.options.selectToDelete")}</span>
                ) : (
                  <span>{t("table.options.deleteSelected")}</span>
                )
              }
            >
              <Button
                data-testid="delete-row-button"
                unstyled
                onClick={deleteRow}
                disabled={!hasSelection}
              >
                <IconComponent
                  name="Trash2"
                  className={cn(
                    "h-5 w-5 transition-all",
                    !hasSelection
                      ? "cursor-not-allowed text-placeholder-foreground"
                      : "text-primary hover:text-status-red",
                  )}
                />
              </Button>
            </ShadTooltip>
          </div>
        )}{" "}
        <div>
          <ShadTooltip content={t("table.options.resetColumns")}>
            <Button
              data-testid="reset-columns-button"
              unstyled
              onClick={() => {
                resetGrid();
              }}
              disabled={!stateChange}
            >
              <IconComponent
                name="RotateCcw"
                strokeWidth={2}
                className={cn(
                  "h-5 w-5 transition-all",
                  !stateChange
                    ? "cursor-not-allowed text-placeholder-foreground"
                    : "text-primary",
                )}
              />
            </Button>
          </ShadTooltip>
        </div>
        {paginationInfo && (
          <div className="ml-2 text-xs text-muted-foreground">
            <ShadTooltip content={t("table.options.paginationInfo")}>
              <span>{paginationInfo}</span>
            </ShadTooltip>
          </div>
        )}
      </div>
    </div>
  );
}
