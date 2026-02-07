import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import {
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  XCircleIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { parseGraphToolResult } from "@/components/assistant-ui/graph-tool";
import useSpacesStore from "@/stores/spacesStore";

export const ToolFallback: ToolCallMessagePartComponent = ({
  toolName,
  argsText,
  result,
  status,
}) => {
  const graphInfo = useMemo(
    () => parseGraphToolResult(toolName, result),
    [toolName, result],
  );
  const activeSpaceId = useSpacesStore((state) => state.activeSpaceId);
  const [isCollapsed, setIsCollapsed] = useState(() => !graphInfo);

  useEffect(() => {
    if (graphInfo) {
      setIsCollapsed(false);
    }
  }, [graphInfo]);

  const isCancelled =
    status?.type === "incomplete" && status.reason === "cancelled";
  const cancelledReason =
    isCancelled && status.error
      ? typeof status.error === "string"
        ? status.error
        : JSON.stringify(status.error)
      : null;

  return (
    <div
      className={cn(
        "aui-tool-fallback-root mb-4 flex w-full flex-col gap-3 rounded-lg border py-3",
        isCancelled && "border-muted-foreground/30 bg-muted/30",
      )}
    >
      <div className="aui-tool-fallback-header flex items-center gap-2 px-4">
        {isCancelled ? (
          <XCircleIcon className="aui-tool-fallback-icon size-4 text-muted-foreground" />
        ) : (
          <CheckIcon className="aui-tool-fallback-icon size-4" />
        )}
        <p
          className={cn(
            "aui-tool-fallback-title grow",
            isCancelled && "text-muted-foreground line-through",
          )}
        >
          {isCancelled ? "Cancelled tool: " : "Used tool: "}
          <b>{toolName}</b>
        </p>
        <Button onClick={() => setIsCollapsed(!isCollapsed)}>
          {isCollapsed ? <ChevronUpIcon /> : <ChevronDownIcon />}
        </Button>
      </div>
      {!isCollapsed && (
        <div className="aui-tool-fallback-content flex flex-col gap-2 border-t pt-2">
          {graphInfo && (
            <div className="aui-tool-fallback-graph-root px-4">
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Knowledge Graph
                </div>
                <p className="mt-2 text-sm">{graphInfo.answer}</p>
                {activeSpaceId && graphInfo.sources?.entity_ids?.length ? (
                  <div className="mt-3">
                    <Button asChild size="sm" variant="secondary">
                      <Link
                        to={`/spaces/${activeSpaceId}/graph?entity_ids=${graphInfo.sources.entity_ids.join(",")}`}
                      >
                        Open in Graph
                      </Link>
                    </Button>
                  </div>
                ) : null}
                {graphInfo.sources && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {graphInfo.sources.entity_ids?.length ? (
                      <span className="rounded-full border px-2 py-0.5">
                        Entities: {graphInfo.sources.entity_ids.join(", ")}
                      </span>
                    ) : null}
                    {graphInfo.sources.document_ids?.length ? (
                      <span className="rounded-full border px-2 py-0.5">
                        Documents: {graphInfo.sources.document_ids.join(", ")}
                      </span>
                    ) : null}
                    {graphInfo.sources.chunk_ids?.length ? (
                      <span className="rounded-full border px-2 py-0.5">
                        Chunks: {graphInfo.sources.chunk_ids.join(", ")}
                      </span>
                    ) : null}
                  </div>
                )}
                {graphInfo.validation && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    Validation: {graphInfo.validation.status || "unknown"}
                  </div>
                )}
                {graphInfo.sources?.paths?.length ? (
                  <div className="mt-3 text-xs text-muted-foreground">
                    Paths: {graphInfo.sources.paths.length}
                  </div>
                ) : null}
              </div>
            </div>
          )}
          {cancelledReason && (
            <div className="aui-tool-fallback-cancelled-root px-4">
              <p className="aui-tool-fallback-cancelled-header font-semibold text-muted-foreground">
                Cancelled reason:
              </p>
              <p className="aui-tool-fallback-cancelled-reason text-muted-foreground">
                {cancelledReason}
              </p>
            </div>
          )}
          <div
            className={cn(
              "aui-tool-fallback-args-root px-4",
              isCancelled && "opacity-60",
            )}
          >
            <pre className="aui-tool-fallback-args-value whitespace-pre-wrap">
              {argsText}
            </pre>
          </div>
          {!isCancelled && result !== undefined && (
            <div className="aui-tool-fallback-result-root border-t border-dashed px-4 pt-2">
              <p className="aui-tool-fallback-result-header font-semibold">
                Result:
              </p>
              <pre className="aui-tool-fallback-result-content whitespace-pre-wrap">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
