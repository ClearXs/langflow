import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import TasksTable from "./components/tasks-table";
import { useGetFlowTasks } from "./use-get-flow-tasks";

interface TasksModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  flowId: string;
}

const TasksModal = ({ open, setOpen, flowId }: TasksModalProps) => {
  const { t } = useTranslation();
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const {
    data: tasksData,
    isLoading,
    error,
    refetch,
  } = useGetFlowTasks(
    flowId,
    open,
    statusFilter === "all" ? undefined : statusFilter,
  );

  useEffect(() => {
    if (open) {
      refetch();
    }
  }, [open, refetch]);

  const handleStatusSelect = (status: string) => {
    setStatusFilter(status);
  };

  // Calculate statistics
  const statistics = useMemo(() => {
    if (!tasksData?.tasks) {
      return {
        total: 0,
        success: 0,
        error: 0,
        successRate: 0,
        totalDataRows: 0,
      };
    }

    const tasks = tasksData.tasks;
    const total = tasks.length;
    const success = tasks.filter((t) => t.status === "success").length;
    const error = tasks.filter((t) => t.status === "error").length;
    const successRate = total > 0 ? ((success / total) * 100).toFixed(1) : "0";
    const totalDataRows = tasks.reduce(
      (sum, t) => sum + (t.total_data_rows || 0),
      0,
    );

    return {
      total,
      success,
      error,
      successRate,
      totalDataRows,
    };
  }, [tasksData]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="flex h-[95vh] max-w-[95vw] flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ForwardedIconComponent name="ListChecks" className="h-5 w-5" />
            {t("tasks.title")}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-1 items-center justify-center">
            <ForwardedIconComponent
              name="Loader2"
              className="h-8 w-8 animate-spin"
            />
            <span className="ml-2">{t("tasks.loading")}</span>
          </div>
        ) : error ? (
          <div className="flex flex-1 items-center justify-center text-destructive">
            <ForwardedIconComponent name="AlertCircle" className="h-5 w-5" />
            <span className="ml-2">
              {t("tasks.error")}: {error.message}
            </span>
          </div>
        ) : tasksData ? (
          <div className="flex flex-1 flex-col gap-3 overflow-hidden">
            {/* Statistics Bar */}
            <div className="flex items-center gap-8 rounded-lg bg-background p-3">
              <div className="flex items-center gap-2">
                <ForwardedIconComponent
                  name="Activity"
                  className="h-4 w-4 text-muted-foreground"
                />
                <span className="text-xs font-medium text-muted-foreground">
                  {t("tasks.stats.totalTasks")}
                </span>
                <span className="text-lg font-bold">{statistics.total}</span>
              </div>

              <div className="flex items-center gap-2">
                <ForwardedIconComponent
                  name="CheckCircle2"
                  className="h-4 w-4 text-success-foreground"
                />
                <span className="text-xs font-medium text-muted-foreground">
                  {t("tasks.stats.success")}
                </span>
                <span className="text-lg font-bold text-success-foreground">
                  {statistics.success}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <ForwardedIconComponent
                  name="XCircle"
                  className="h-4 w-4 text-destructive"
                />
                <span className="text-xs font-medium text-muted-foreground">
                  {t("tasks.stats.error")}
                </span>
                <span className="text-lg font-bold text-destructive">
                  {statistics.error}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <ForwardedIconComponent
                  name="TrendingUp"
                  className="h-4 w-4 text-muted-foreground"
                />
                <span className="text-xs font-medium text-muted-foreground">
                  {t("tasks.stats.successRate")}
                </span>
                <span className="text-lg font-bold">
                  {statistics.successRate}%
                </span>
              </div>

              <div className="flex items-center gap-2">
                <ForwardedIconComponent
                  name="Database"
                  className="h-4 w-4 text-muted-foreground"
                />
                <span className="text-xs font-medium text-muted-foreground">
                  {t("tasks.stats.totalDataRows")}
                </span>
                <span className="text-lg font-bold">
                  {statistics.totalDataRows.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Filter Controls */}
            <div className="flex items-center gap-3 rounded-lg border bg-background p-3">
              <ForwardedIconComponent
                name="Filter"
                className="h-4 w-4 text-muted-foreground flex-shrink-0"
              />
              <Select value={statusFilter} onValueChange={handleStatusSelect}>
                <SelectTrigger className="w-[140px] flex-shrink-0">
                  <SelectValue placeholder={t("tasks.selectStatus")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("tasks.allStatus")}</SelectItem>
                  <SelectItem value="running">
                    {t("tasks.status.running")}
                  </SelectItem>
                  <SelectItem value="success">
                    {t("tasks.status.success")}
                  </SelectItem>
                  <SelectItem value="error">
                    {t("tasks.status.error")}
                  </SelectItem>
                </SelectContent>
              </Select>

              <div className="ml-auto text-sm text-muted-foreground whitespace-nowrap flex-shrink-0">
                {t("tasks.totalCount", { count: tasksData.total })}
              </div>
            </div>

            {/* Tasks Table */}
            <div className="flex-1 overflow-hidden">
              <TasksTable tasks={tasksData.tasks} flowId={flowId} />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            {t("tasks.noTasks")}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default TasksModal;
