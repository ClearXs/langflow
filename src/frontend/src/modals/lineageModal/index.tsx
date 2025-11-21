import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import LineageGraph from "./components/lineage-graph";
import { useGetLineage } from "./use-get-lineage";

interface LineageModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  flowId: string;
}

const LineageModal = ({ open, setOpen, flowId }: LineageModalProps) => {
  const { t } = useTranslation();
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  const {
    data: lineageData,
    isLoading,
    error,
    refetch,
  } = useGetLineage(flowId, selectedTable || undefined);

  useEffect(() => {
    if (open) {
      refetch();
    }
  }, [open, refetch]);

  const allTables = lineageData?.tables || [];

  const handleTableSelect = (tableId: string | null) => {
    setSelectedTable(tableId);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="flex h-[85vh] max-w-[90vw] flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ForwardedIconComponent name="GitBranch" className="h-5 w-5" />
            {t("lineage.title")}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-1 items-center justify-center">
            <ForwardedIconComponent
              name="Loader2"
              className="h-8 w-8 animate-spin"
            />
            <span className="ml-2">{t("lineage.analyzing")}</span>
          </div>
        ) : error ? (
          <div className="flex flex-1 items-center justify-center text-destructive">
            <ForwardedIconComponent name="AlertCircle" className="h-5 w-5" />
            <span className="ml-2">
              {t("lineage.error")}: {error.message}
            </span>
          </div>
        ) : lineageData ? (
          <div className="flex flex-1 flex-col gap-3 overflow-hidden">
            {/* Filter Controls */}
            <div className="flex items-center gap-3">
              <Select
                value={selectedTable || "all"}
                onValueChange={(value) =>
                  handleTableSelect(value === "all" ? null : value)
                }
              >
                <SelectTrigger className="w-[250px]">
                  <SelectValue placeholder={t("lineage.selectTable")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("lineage.allTables")}</SelectItem>
                  {allTables.map((table) => (
                    <SelectItem key={table.id} value={table.table_name}>
                      {table.table_name} (
                      {table.type === "source"
                        ? t("lineage.source")
                        : t("lineage.target")}
                      ) - {table.node_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <div className="text-sm text-muted-foreground">
                {t("lineage.totalTables")}: {lineageData.total_tables} |
                {t("lineage.totalRelationships")}:{" "}
                {lineageData.total_relationships}
              </div>
            </div>

            {/* Main Content - Full Width Graph */}
            <div className="flex-1 overflow-hidden">
              <div className="h-full overflow-hidden rounded-md border">
                <LineageGraph
                  tables={allTables}
                  relationships={lineageData.relationships}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            {t("lineage.noData")}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default LineageModal;
