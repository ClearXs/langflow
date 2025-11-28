import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { convertUTCToLocalTimezone } from "@/utils/utils";
import ComponentsList from "./components-list";

interface Task {
  id: string;
  run_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
  total_components: number;
  success_components: number;
  error_components: number;
  total_data_rows: number;
  total_duration_ms?: number;
}

interface TasksTableProps {
  tasks: Task[];
  flowId: string;
}

const TasksTable = ({ tasks }: TasksTableProps) => {
  const { t } = useTranslation();
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

  const toggleExpand = (taskId: string) => {
    setExpandedTaskId(expandedTaskId === taskId ? null : taskId);
  };

  const formatDateTime = (dateString: string) => {
    return convertUTCToLocalTimezone(dateString);
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return t("tasks.noDuration");
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "success":
        return (
          <Badge
            variant="default"
            className="bg-success-background text-success-foreground hover:bg-success-background"
          >
            {t("tasks.status.success")}
          </Badge>
        );
      case "error":
        return <Badge variant="destructive">{t("tasks.status.error")}</Badge>;
      case "running":
        return (
          <Badge variant="secondary" className="bg-blue-100 text-blue-700">
            {t("tasks.status.running")}
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (!tasks || tasks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        {t("tasks.noTasks")}
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px]"></TableHead>
            <TableHead className="w-[120px]">{t("tasks.runId")}</TableHead>
            <TableHead className="w-[180px]">
              {t("tasks.executionTime")}
            </TableHead>
            <TableHead className="w-[120px]">
              {t("tasks.status.title")}
            </TableHead>
            <TableHead className="w-[100px] text-center">
              {t("tasks.totalComponents")}
            </TableHead>
            <TableHead className="w-[100px] text-center">
              {t("tasks.stats.success")}
            </TableHead>
            <TableHead className="w-[100px] text-center">
              {t("tasks.stats.error")}
            </TableHead>
            <TableHead className="w-[120px] text-right">
              {t("tasks.duration")}
            </TableHead>
            <TableHead className="w-[120px] text-right">
              {t("tasks.dataRows")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => {
            const isExpanded = expandedTaskId === task.id;
            return (
              <>
                <TableRow
                  key={task.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => toggleExpand(task.id)}
                >
                  <TableCell>
                    <ForwardedIconComponent
                      name={isExpanded ? "ChevronDown" : "ChevronRight"}
                      className="h-4 w-4 text-muted-foreground"
                    />
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    <span className="text-muted-foreground" title={task.id}>
                      {task.id.substring(0, 8)}...
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {formatDateTime(task.created_at)}
                  </TableCell>
                  <TableCell>{getStatusBadge(task.status)}</TableCell>
                  <TableCell className="text-center font-medium">
                    {task.total_components}
                  </TableCell>
                  <TableCell className="text-center text-success-foreground">
                    {task.success_components}
                  </TableCell>
                  <TableCell className="text-center text-destructive">
                    {task.error_components}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {formatDuration(task.total_duration_ms)}
                  </TableCell>
                  <TableCell className="text-right">
                    {task.total_data_rows.toLocaleString()}
                  </TableCell>
                </TableRow>
                {isExpanded && (
                  <TableRow>
                    <TableCell colSpan={9} className="bg-muted/20 p-0">
                      <div className="p-4">
                        <ComponentsList taskId={task.id} />
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </>
            );
          })}
        </TableBody>
      </Table>
    </ScrollArea>
  );
};

export default TasksTable;
