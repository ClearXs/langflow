import { useState } from "react";
import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGetTaskDetail } from "../use-get-task-detail";

interface ComponentsListProps {
  taskId: string;
}

const ComponentsList = ({ taskId }: ComponentsListProps) => {
  const { t } = useTranslation();
  const [expandedComponents, setExpandedComponents] = useState<Set<string>>(
    new Set(),
  );
  const { data: taskDetail, isLoading } = useGetTaskDetail(taskId, true);

  const toggleComponent = (componentId: string) => {
    setExpandedComponents((prev) => {
      const next = new Set(prev);
      if (next.has(componentId)) {
        next.delete(componentId);
      } else {
        next.add(componentId);
      }
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return (
          <ForwardedIconComponent
            name="CheckCircle2"
            className="h-3 w-3 text-success"
          />
        );
      case "error":
        return (
          <ForwardedIconComponent
            name="XCircle"
            className="h-3 w-3 text-destructive"
          />
        );
      case "running":
        return (
          <ForwardedIconComponent
            name="Loader2"
            className="h-3 w-3 animate-spin"
          />
        );
      default:
        return <ForwardedIconComponent name="Circle" className="h-3 w-3" />;
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
      <Badge variant={variant} className="ml-2 text-xs">
        {t(`tasks.status.${status}`)}
      </Badge>
    );
  };

  const getComponentName = (transaction: any) => {
    // Try to get component name from metadata
    if (transaction.inputs?._metadata?.component_name) {
      return transaction.inputs._metadata.component_name;
    }
    // Fallback to vertex_id
    return transaction.vertex_id;
  };

  const formatJSON = (data: any) => {
    if (!data) return "null";
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <ForwardedIconComponent
          name="Loader2"
          className="h-5 w-5 animate-spin"
        />
        <span className="ml-2 text-sm text-muted-foreground">
          {t("tasks.loadingComponents")}
        </span>
      </div>
    );
  }

  if (
    !taskDetail ||
    !taskDetail.transactions ||
    taskDetail.transactions.length === 0
  ) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <ForwardedIconComponent
          name="Inbox"
          className="h-12 w-12 text-muted-foreground/40 mb-3"
        />
        <p className="text-sm font-medium text-muted-foreground">
          {t("tasks.noComponents")}
        </p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          {t("tasks.noComponentsDesc")}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold flex items-center gap-2">
        <ForwardedIconComponent name="Layers" className="h-4 w-4" />
        {t("tasks.componentsList")}
      </h4>
      <ScrollArea className="h-[400px] pr-4">
        <div className="space-y-2">
          {taskDetail.transactions.map((transaction: any) => {
            const isExpanded = expandedComponents.has(transaction.id);

            return (
              <Collapsible
                key={transaction.id}
                open={isExpanded}
                onOpenChange={() => toggleComponent(transaction.id)}
              >
                <div className="border rounded-lg bg-background hover:shadow-sm transition-shadow">
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center justify-between p-3 hover:bg-muted/30 cursor-pointer transition-colors">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {getStatusIcon(transaction.status)}
                        <span className="text-sm font-medium truncate">
                          {getComponentName(transaction)}
                        </span>
                        {getStatusBadge(transaction.status)}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 flex-shrink-0"
                      >
                        <ForwardedIconComponent
                          name={isExpanded ? "ChevronUp" : "ChevronDown"}
                          className="h-3 w-3"
                        />
                      </Button>
                    </div>
                  </CollapsibleTrigger>

                  <CollapsibleContent>
                    <div className="border-t p-4 space-y-4 bg-muted/20">
                      {/* Timestamp */}
                      <div className="flex items-center gap-2">
                        <ForwardedIconComponent
                          name="Clock"
                          className="h-3.5 w-3.5 text-muted-foreground"
                        />
                        <span className="text-xs font-medium text-muted-foreground">
                          {t("tasks.timestamp")}:
                        </span>
                        <span className="text-xs">
                          {new Date(transaction.timestamp).toLocaleString()}
                        </span>
                      </div>

                      {/* Error message if present */}
                      {transaction.error && (
                        <div className="bg-destructive/10 border border-destructive/20 p-3 rounded-md">
                          <div className="flex items-center gap-2 mb-2">
                            <ForwardedIconComponent
                              name="AlertCircle"
                              className="h-4 w-4 text-destructive"
                            />
                            <div className="text-xs font-semibold text-destructive">
                              {t("tasks.errorMessage")}
                            </div>
                          </div>
                          <div className="text-xs text-destructive/90 font-mono bg-destructive/5 p-2 rounded">
                            {transaction.error}
                          </div>
                        </div>
                      )}

                      {/* Inputs */}
                      {transaction.inputs && (
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <ForwardedIconComponent
                              name="ArrowDown"
                              className="h-3.5 w-3.5 text-blue-500"
                            />
                            <span className="text-xs font-semibold text-foreground">
                              {t("tasks.inputs")}
                            </span>
                          </div>
                          <pre className="text-xs bg-muted/50 border p-3 rounded-md max-h-[200px] overflow-y-auto font-mono whitespace-pre-wrap break-all max-w-full">
                            {formatJSON(transaction.inputs)}
                          </pre>
                        </div>
                      )}

                      {/* Outputs */}
                      {transaction.outputs && (
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <ForwardedIconComponent
                              name="ArrowUp"
                              className="h-3.5 w-3.5 text-green-500"
                            />
                            <span className="text-xs font-semibold text-foreground">
                              {t("tasks.outputs")}
                            </span>
                          </div>
                          <pre className="text-xs bg-muted/50 border p-3 rounded-md max-h-[200px] overflow-y-auto font-mono whitespace-pre-wrap break-all max-w-full">
                            {formatJSON(transaction.outputs)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </CollapsibleContent>
                </div>
              </Collapsible>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

export default ComponentsList;
