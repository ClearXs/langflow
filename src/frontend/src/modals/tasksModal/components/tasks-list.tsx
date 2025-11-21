import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { TaskResponse } from "../types";
import ComponentsList from "./components-list";

interface TasksListProps {
  tasks: TaskResponse[];
  flowId: string;
}

const TasksList = ({ tasks }: TasksListProps) => {
  const { t } = useTranslation();
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  const toggleTask = (taskId: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return (
          <ForwardedIconComponent
            name="Loader2"
            className="h-4 w-4 animate-spin"
          />
        );
      case "success":
        return (
          <ForwardedIconComponent
            name="CheckCircle"
            className="h-4 w-4 text-success"
          />
        );
      case "error":
        return (
          <ForwardedIconComponent
            name="XCircle"
            className="h-4 w-4 text-destructive"
          />
        );
      default:
        return <ForwardedIconComponent name="Circle" className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variant =
      status === "success"
        ? "success"
        : status === "error"
          ? "destructive"
          : "default";

    return (
      <Badge variant={variant} className="ml-2">
        {t(`tasks.status.${status}`)}
      </Badge>
    );
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return t("tasks.noDuration");
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <ForwardedIconComponent name="ListX" className="h-12 w-12 mb-4" />
        <p>{t("tasks.noTasksFound")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => {
        const isExpanded = expandedTasks.has(task.id);
        const successRate =
          task.total_components > 0
            ? ((task.success_components / task.total_components) * 100).toFixed(
                0,
              )
            : 0;

        return (
          <Card
            key={task.id}
            className="border-l-4"
            style={{
              borderLeftColor:
                task.status === "success"
                  ? "rgb(34, 197, 94)"
                  : task.status === "error"
                    ? "rgb(239, 68, 68)"
                    : "rgb(59, 130, 246)",
            }}
          >
            <Collapsible
              open={isExpanded}
              onOpenChange={() => toggleTask(task.id)}
            >
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      {getStatusIcon(task.status)}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-base font-semibold">
                            {formatDistanceToNow(new Date(task.created_at), {
                              addSuffix: true,
                            })}
                          </span>
                          {getStatusBadge(task.status)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {t("tasks.runId")}: {task.run_id.substring(0, 8)}...
                        </div>

                        {/* Summary Statistics Bar */}
                        <div className="mt-2 flex items-center gap-4 text-xs">
                          <div className="flex items-center gap-1">
                            <ForwardedIconComponent
                              name="Box"
                              className="h-3 w-3"
                            />
                            <span className="font-medium">
                              {task.total_components}
                            </span>
                            <span className="text-muted-foreground">
                              {t("tasks.components")}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 text-success">
                            <ForwardedIconComponent
                              name="CheckCircle2"
                              className="h-3 w-3"
                            />
                            <span className="font-medium">
                              {task.success_components}
                            </span>
                          </div>
                          {task.error_components > 0 && (
                            <div className="flex items-center gap-1 text-destructive">
                              <ForwardedIconComponent
                                name="XCircle"
                                className="h-3 w-3"
                              />
                              <span className="font-medium">
                                {task.error_components}
                              </span>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <ForwardedIconComponent
                              name="Gauge"
                              className="h-3 w-3"
                            />
                            <span className="font-medium">{successRate}%</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <ForwardedIconComponent
                              name="Clock"
                              className="h-3 w-3"
                            />
                            <span className="font-medium">
                              {formatDuration(task.total_duration_ms)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 flex-shrink-0 -mt-1"
                    >
                      <ForwardedIconComponent
                        name={isExpanded ? "ChevronUp" : "ChevronDown"}
                        className="h-4 w-4"
                      />
                    </Button>
                  </div>
                </CardHeader>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <CardContent className="border-t pt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-semibold mb-2">
                        {t("tasks.statistics")}
                      </h4>
                      <dl className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.totalComponents")}:
                          </dt>
                          <dd className="font-medium">
                            {task.total_components}
                          </dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.successComponents")}:
                          </dt>
                          <dd className="font-medium text-success">
                            {task.success_components}
                          </dd>
                        </div>
                        {task.error_components > 0 && (
                          <div className="flex justify-between">
                            <dt className="text-muted-foreground">
                              {t("tasks.errorComponents")}:
                            </dt>
                            <dd className="font-medium text-destructive">
                              {task.error_components}
                            </dd>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.duration")}:
                          </dt>
                          <dd className="font-medium">
                            {formatDuration(task.total_duration_ms)}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div>
                      <h4 className="text-sm font-semibold mb-2">
                        {t("tasks.dataStats")}
                      </h4>
                      <dl className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.totalRows")}:
                          </dt>
                          <dd className="font-medium">
                            {task.total_data_rows.toLocaleString()}
                          </dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.totalSize")}:
                          </dt>
                          <dd className="font-medium">
                            {task.total_data_size_mb.toFixed(2)} MB
                          </dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">
                            {t("tasks.exchanges")}:
                          </dt>
                          <dd className="font-medium">
                            {task.total_exchanges}
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </div>

                  {task.first_error_message && (
                    <div className="mt-4 p-3 bg-destructive/10 rounded-md">
                      <h4 className="text-sm font-semibold text-destructive mb-1">
                        {t("tasks.errorMessage")}
                      </h4>
                      <p className="text-sm text-destructive/80">
                        {task.first_error_message}
                      </p>
                      {task.first_error_component_id && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {t("tasks.errorComponent")}:{" "}
                          {task.first_error_component_id}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Components List */}
                  {isExpanded && <ComponentsList taskId={task.id} />}
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        );
      })}
    </div>
  );
};

export default TasksList;
