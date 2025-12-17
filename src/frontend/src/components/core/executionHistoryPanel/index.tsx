import {
  Copy,
  Download,
  Maximize2,
  Minimize2,
  RefreshCw,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import useAlertStore from "@/stores/alertStore";
import useFlowStore from "@/stores/flowStore";
import { transformOutputData } from "./dataTransform";
import { copyToClipboard, exportAsCSV, exportAsJSON } from "./exportUtils";
import OutputSelector from "./outputSelector";
import OutputTable from "./outputTable";
import { useExecutionData } from "./useExecutionData";

export default function ExecutionHistoryPanel() {
  const { t } = useTranslation();
  const setOpen = useFlowStore((state) => state.setExecutionHistoryOpen);
  const selectedNodeId = useFlowStore((state) => state.selectedNodeId);
  const nodes = useFlowStore((state) => state.nodes);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const isMaximized = useFlowStore(
    (state) => state.isExecutionHistoryMaximized,
  );
  const setMaximized = useFlowStore(
    (state) => state.setExecutionHistoryMaximized,
  );

  const [viewMode, setViewMode] = useState<"results" | "all">("results");
  const { outputs, rawTransaction } = useExecutionData(
    selectedNodeId,
    viewMode,
  );
  const [selectedOutputIndex, setSelectedOutputIndex] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 获取节点名称
  const nodeName = useMemo(() => {
    if (!selectedNodeId) return null;
    const node = nodes.find((n) => n.id === selectedNodeId);
    return node?.data?.node?.display_name || node?.data?.type || selectedNodeId;
  }, [selectedNodeId, nodes]);

  const currentOutput = outputs[selectedOutputIndex];
  const tableData = useMemo(
    () => (currentOutput ? transformOutputData(currentOutput.data) : null),
    [currentOutput],
  );

  // Handle refresh
  const handleRefresh = () => {
    setIsRefreshing(true);
    // Simulate refresh animation
    setTimeout(() => {
      setIsRefreshing(false);
      setSuccessData({ title: t("executionHistory.dataRefreshed") });
    }, 500);
  };

  // Handle export as JSON
  const handleExportJSON = () => {
    if (!currentOutput) return;
    try {
      const filename = `${nodeName || "output"}-${currentOutput.name}`;
      exportAsJSON(currentOutput.data, filename);
      setSuccessData({ title: t("executionHistory.exportSuccess") });
    } catch {
      setErrorData({ title: t("executionHistory.exportFailed") });
    }
  };

  // Handle export as CSV
  const handleExportCSV = () => {
    if (!tableData) return;
    try {
      const filename = `${nodeName || "output"}-${currentOutput.name}`;
      exportAsCSV(tableData.columns, tableData.rows, filename);
      setSuccessData({ title: t("executionHistory.exportSuccess") });
    } catch {
      setErrorData({ title: t("executionHistory.exportFailed") });
    }
  };

  // Handle copy to clipboard
  const handleCopy = async () => {
    if (!currentOutput) return;
    const success = await copyToClipboard(currentOutput.data);
    if (success) {
      setSuccessData({ title: t("executionHistory.copiedToClipboard") });
    } else {
      setErrorData({ title: t("executionHistory.copyFailed") });
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">
            {t("executionHistory.title")}
          </h3>
          {nodeName && (
            <span className="text-xs text-muted-foreground">- {nodeName}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* 视图模式选择器 */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap">
              {t("executionHistory.viewMode")}:
            </label>
            <Select
              value={viewMode}
              onValueChange={(value: "results" | "all") => setViewMode(value)}
            >
              <SelectTrigger className="h-7 w-[120px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="results">
                  {t("executionHistory.resultsOnly")}
                </SelectItem>
                <SelectItem value="all">
                  {t("executionHistory.allData")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 输出选择器（多输出时） */}
          {outputs.length > 1 && (
            <OutputSelector
              outputs={outputs}
              selectedIndex={selectedOutputIndex}
              onSelect={setSelectedOutputIndex}
            />
          )}

          {/* 操作按钮组 */}
          {tableData && (
            <div className="flex items-center gap-1">
              {/* 刷新按钮 */}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={handleRefresh}
                disabled={isRefreshing}
                title={t("executionHistory.refresh")}
              >
                <RefreshCw
                  className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
                />
              </Button>

              {/* 复制按钮 */}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={handleCopy}
                title={t("executionHistory.copy")}
              >
                <Copy className="h-4 w-4" />
              </Button>

              {/* 导出下拉菜单 */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    title={t("executionHistory.export")}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleExportJSON}>
                    {t("executionHistory.exportJSON")}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleExportCSV}>
                    {t("executionHistory.exportCSV")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}

          {/* 最大化/最小化按钮 */}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setMaximized(!isMaximized)}
            title={
              isMaximized
                ? t("executionHistory.minimize")
                : t("executionHistory.maximize")
            }
          >
            {isMaximized ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>

          {/* 关闭按钮 */}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {tableData ? (
          <OutputTable columns={tableData.columns} rows={tableData.rows} />
        ) : (
          <div className="flex h-full items-center justify-center p-4 text-sm text-muted-foreground">
            {selectedNodeId
              ? t("executionHistory.noData")
              : t("executionHistory.selectNode")}
          </div>
        )}
      </div>
    </div>
  );
}
