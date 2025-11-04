import { useMemo, useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useGetDataExchangeStats } from "@/controllers/API/queries/data-exchange";
import {
  useGetExecutionLogsQuery,
  useGetExecutionStatsQuery,
} from "@/controllers/API/queries/transactions/use-get-execution-logs";
import { convertUTCToLocalTimezone } from "@/utils/utils";

interface ExecutionLogsComponentProps {
  flowId: string;
}

const STATUS_CONFIG = {
  success: {
    label: "成功",
    color: "text-green-700",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    icon: "CheckCircle2",
  },
  error: {
    label: "失败",
    color: "text-red-700",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    icon: "XCircle",
  },
  running: {
    label: "运行中",
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: "Loader2",
  },
};

const COMPONENT_TYPE_MAP: Record<string, string> = {
  etl_input: "输入",
  etl_transformation: "转换",
  etl_operation: "操作",
  etl_output: "输出",
  model: "模型",
  agent: "智能体",
  tool: "工具",
  vector: "向量",
  prompt: "提示词",
  data: "数据",
  other: "其他",
};

export default function ExecutionLogsComponent({
  flowId,
}: ExecutionLogsComponentProps) {
  const [componentType, setComponentType] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // 获取执行统计
  const { data: stats } = useGetExecutionStatsQuery({
    flowId,
  });

  // 获取数据交换统计
  const { data: exchangeStats } = useGetDataExchangeStats(flowId);

  // 获取执行日志
  const {
    data: logs,
    isLoading: logsLoading,
    refetch,
  } = useGetExecutionLogsQuery({
    flowId,
    componentType: componentType === "all" ? undefined : componentType,
    status: status === "all" ? undefined : status,
    limit: 100,
  });

  // 计算流程级数据统计
  const flowDataStats = useMemo(() => {
    if (!logs)
      return {
        total_rows: 0,
        total_fields: 0,
        total_data_size: 0,
        components_with_data: 0,
      };

    let totalRows = 0;
    let totalFields = 0;
    let totalDataSize = 0;
    let componentsWithData = 0;

    logs.forEach((log) => {
      const dataMetrics = log.outputs?._metadata?.data_metrics;
      if (dataMetrics) {
        if (dataMetrics.row_count !== undefined) {
          totalRows += dataMetrics.row_count;
          componentsWithData++;
        }
        if (dataMetrics.field_count !== undefined) {
          totalFields += dataMetrics.field_count;
        }
        if (dataMetrics.data_size !== undefined) {
          totalDataSize += dataMetrics.data_size;
        }
      }
    });

    return {
      total_rows: totalRows,
      total_fields: totalFields,
      total_data_size: totalDataSize,
      components_with_data: componentsWithData,
    };
  }, [logs]);

  // 过滤日志
  const filteredLogs = useMemo(() => {
    if (!logs) return [];

    return logs.filter((log) => {
      const componentMatch =
        !searchTerm ||
        log.inputs?._metadata?.component_name
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase()) ||
        log.vertex_id?.toLowerCase().includes(searchTerm.toLowerCase());

      return componentMatch;
    });
  }, [logs, searchTerm]);

  // 格式化持续时间 - 保留3位小数
  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return "-";
    if (durationMs < 1000) return `${durationMs.toFixed(3)}ms`;
    return `${(durationMs / 1000).toFixed(3)}s`;
  };

  // 格式化数据大小
  const formatDataSize = (bytes?: number) => {
    if (!bytes) return "0 B";
    const kb = bytes / 1024;
    if (kb < 1) return `${bytes} B`;
    const mb = kb / 1024;
    if (mb < 1) return `${kb.toFixed(2)} KB`;
    const gb = mb / 1024;
    if (gb < 1) return `${mb.toFixed(2)} MB`;
    return `${gb.toFixed(2)} GB`;
  };

  // 格式化JSON
  const formatJSON = (data: any) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className="space-y-4">
      {/* 紧凑的统计栏 */}
      <div className="flex items-center justify-between bg-muted/30 rounded-lg p-4">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <IconComponent
              name="Activity"
              className="h-4 w-4 text-muted-foreground"
            />
            <span className="text-sm font-medium">总次数</span>
            <span className="text-lg font-bold">
              {stats?.total_executions || 0}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <IconComponent
              name="CheckCircle2"
              className="h-4 w-4 text-green-600"
            />
            <span className="text-sm font-medium text-green-700">成功</span>
            <span className="text-lg font-bold text-green-700">
              {stats?.successful_executions || 0}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <IconComponent name="XCircle" className="h-4 w-4 text-red-600" />
            <span className="text-sm font-medium text-red-700">失败</span>
            <span className="text-lg font-bold text-red-700">
              {stats?.failed_executions || 0}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <IconComponent
              name="TrendingUp"
              className="h-4 w-4 text-muted-foreground"
            />
            <span className="text-sm font-medium">成功率</span>
            <span className="text-lg font-bold">
              {stats?.success_rate.toFixed(1) || 0}%
            </span>
          </div>
        </div>

        {/* 流程级数据统计 */}
        {flowDataStats.components_with_data > 0 && (
          <div className="flex items-center gap-6 border-l pl-6">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2">
                    <IconComponent
                      name="Database"
                      className="h-4 w-4 text-orange-600"
                    />
                    <span className="text-sm font-medium text-orange-700">
                      总数据行数
                    </span>
                    <span className="text-lg font-bold text-orange-700">
                      {flowDataStats.total_rows.toLocaleString()}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <div>涉及组件: {flowDataStats.components_with_data} 个</div>
                    <div>
                      总字段数: {flowDataStats.total_fields.toLocaleString()} 个
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2">
                    <IconComponent
                      name="HardDrive"
                      className="h-4 w-4 text-cyan-600"
                    />
                    <span className="text-sm font-medium text-cyan-700">
                      总数据大小
                    </span>
                    <span className="text-lg font-bold text-cyan-700">
                      {formatDataSize(flowDataStats.total_data_size)}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <div>
                      平均每组件:{" "}
                      {flowDataStats.components_with_data > 0
                        ? formatDataSize(
                            Math.round(
                              flowDataStats.total_data_size /
                                flowDataStats.components_with_data,
                            ),
                          )
                        : "0 B"}
                    </div>
                    <div>
                      总字段数: {flowDataStats.total_fields.toLocaleString()} 个
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* 数据交换统计 */}
        {exchangeStats && exchangeStats.total_exchanges > 0 && (
          <div className="flex items-center gap-6 border-l pl-6">
            <div className="flex items-center gap-2">
              <IconComponent
                name="ArrowLeftRight"
                className="h-4 w-4 text-blue-600"
              />
              <span className="text-sm font-medium text-blue-700">
                数据交换
              </span>
              <span className="text-lg font-bold text-blue-700">
                {exchangeStats.total_exchanges}
              </span>
            </div>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2">
                    <IconComponent
                      name="Database"
                      className="h-4 w-4 text-purple-600"
                    />
                    <span className="text-sm font-medium text-purple-700">
                      总数据量
                    </span>
                    <span className="text-lg font-bold text-purple-700">
                      {formatDataSize(exchangeStats.total_data_size)}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <div>
                      平均大小: {formatDataSize(exchangeStats.avg_data_size)}
                    </div>
                    <div>源组件数: {exchangeStats.unique_source_vertices}</div>
                    <div>
                      目标组件数: {exchangeStats.unique_target_vertices}
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        <Button onClick={() => refetch()} variant="outline" size="sm">
          <IconComponent name="RefreshCw" className="h-3.5 w-3.5 mr-1.5" />
          刷新
        </Button>
      </div>

      {/* 紧凑的过滤器 */}
      <div className="flex items-center gap-3 bg-background border rounded-lg p-3">
        <IconComponent
          name="Filter"
          className="h-4 w-4 text-muted-foreground"
        />

        <Select value={componentType} onValueChange={setComponentType}>
          <SelectTrigger className="w-[140px] h-8">
            <SelectValue placeholder="组件类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有类型</SelectItem>
            {stats?.component_types &&
              Object.entries(stats.component_types).map(([type, count]) => (
                <SelectItem key={type} value={type}>
                  {COMPONENT_TYPE_MAP[type] || type} ({count})
                </SelectItem>
              ))}
          </SelectContent>
        </Select>

        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-[140px] h-8">
            <SelectValue placeholder="执行状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有状态</SelectItem>
            <SelectItem value="success">成功</SelectItem>
            <SelectItem value="error">失败</SelectItem>
            <SelectItem value="running">运行中</SelectItem>
          </SelectContent>
        </Select>

        <Input
          placeholder="搜索组件名称或ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="h-8 flex-1"
        />
      </div>

      {/* Table展示日志 */}
      <div className="border rounded-lg overflow-hidden">
        {logsLoading ? (
          <div className="flex items-center justify-center py-12">
            <IconComponent
              name="Loader2"
              className="h-6 w-6 animate-spin text-muted-foreground"
            />
            <span className="ml-2 text-sm text-muted-foreground">
              加载中...
            </span>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-12">
            <IconComponent
              name="Inbox"
              className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-30"
            />
            <div className="text-sm text-muted-foreground">暂无执行日志</div>
            {searchTerm && (
              <div className="text-xs text-muted-foreground mt-1">
                没有找到匹配 "{searchTerm}" 的日志
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-auto max-h-[600px]">
            <table className="w-full">
              <thead className="bg-muted/50 sticky top-0 z-10">
                <tr className="border-b">
                  <th className="text-left py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    组件名称
                  </th>
                  <th className="text-left py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    类型
                  </th>
                  <th className="text-left py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    状态
                  </th>
                  <th className="text-right py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    执行时长
                  </th>
                  <th className="text-right py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    时间戳
                  </th>
                  <th className="text-center py-2.5 px-4 text-xs font-semibold text-muted-foreground whitespace-nowrap w-24">
                    输入/输出
                  </th>
                  <th className="text-center py-2.5 px-4 text-xs font-semibold text-muted-foreground w-16">
                    详情
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => {
                  const isExpanded = expandedRow === log.transaction_id;
                  const statusConfig =
                    STATUS_CONFIG[log.status as keyof typeof STATUS_CONFIG];

                  return (
                    <>
                      <tr
                        key={log.transaction_id}
                        className="border-b hover:bg-muted/30 transition-colors"
                      >
                        <td className="py-2.5 px-4">
                          <div className="text-sm font-medium truncate max-w-[200px]">
                            {log.inputs?._metadata?.component_name ||
                              "未知组件"}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            ID: {log.vertex_id.slice(0, 8)}...
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          <Badge
                            variant="outline"
                            className="text-xs font-normal whitespace-nowrap"
                          >
                            {COMPONENT_TYPE_MAP[
                              log.inputs?._metadata?.component_type || "other"
                            ] || "其他"}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md border whitespace-nowrap">
                            <div
                              className={`flex items-center gap-1.5 ${statusConfig?.bgColor} ${statusConfig?.borderColor} px-2 py-0.5 rounded`}
                            >
                              <IconComponent
                                name={statusConfig?.icon || "HelpCircle"}
                                className={`h-3 w-3 flex-shrink-0 ${statusConfig?.color} ${
                                  log.status === "running" ? "animate-spin" : ""
                                }`}
                              />
                              <span
                                className={`text-xs font-medium ${statusConfig?.color}`}
                              >
                                {statusConfig?.label || log.status}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          <div className="text-sm font-mono whitespace-nowrap">
                            {formatDuration(
                              log.outputs?._metadata?.execution_duration_ms,
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          <div className="text-xs text-muted-foreground whitespace-nowrap">
                            {convertUTCToLocalTimezone(log.timestamp)}
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          <TooltipProvider>
                            <div className="flex items-center justify-center gap-2">
                              {/* 输入信息 Tooltip */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div className="cursor-pointer p-1 hover:bg-muted rounded">
                                    <IconComponent
                                      name="ArrowDownToLine"
                                      className="h-4 w-4 text-blue-600"
                                    />
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent
                                  side="left"
                                  className="max-w-md max-h-96 overflow-auto"
                                >
                                  <div className="space-y-2">
                                    <div className="font-semibold text-sm mb-2">
                                      输入信息
                                    </div>
                                    <pre className="text-xs font-mono bg-muted/50 p-2 rounded overflow-x-auto">
                                      {formatJSON(log.inputs)}
                                    </pre>
                                  </div>
                                </TooltipContent>
                              </Tooltip>

                              {/* 输出信息 Tooltip */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div className="cursor-pointer p-1 hover:bg-muted rounded">
                                    <IconComponent
                                      name="ArrowUpFromLine"
                                      className="h-4 w-4 text-green-600"
                                    />
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent
                                  side="left"
                                  className="max-w-md max-h-96 overflow-auto"
                                >
                                  <div className="space-y-2">
                                    <div className="font-semibold text-sm mb-2">
                                      输出信息
                                    </div>
                                    <pre className="text-xs font-mono bg-muted/50 p-2 rounded overflow-x-auto">
                                      {formatJSON(log.outputs)}
                                    </pre>
                                  </div>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </TooltipProvider>
                        </td>
                        <td className="py-2.5 px-4 text-center">
                          <button
                            onClick={() =>
                              setExpandedRow(
                                isExpanded ? null : log.transaction_id,
                              )
                            }
                            className="p-1 hover:bg-muted rounded transition-colors"
                          >
                            <IconComponent
                              name={isExpanded ? "ChevronUp" : "ChevronDown"}
                              className="h-4 w-4 text-muted-foreground mx-auto"
                            />
                          </button>
                        </td>
                      </tr>

                      {/* 展开的详细信息 */}
                      {isExpanded && (
                        <tr className="bg-muted/20">
                          <td colSpan={7} className="p-4">
                            <div className="space-y-4">
                              {/* 错误信息 */}
                              {log.error && (
                                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                                  <div className="flex items-center gap-2 text-red-800 mb-1">
                                    <IconComponent
                                      name="AlertCircle"
                                      className="h-4 w-4"
                                    />
                                    <span className="text-sm font-semibold">
                                      错误信息
                                    </span>
                                  </div>
                                  <div className="text-xs text-red-700 font-mono">
                                    {log.error}
                                  </div>
                                </div>
                              )}

                              {/* 性能指标 */}
                              <div className="grid grid-cols-4 gap-4">
                                {log.outputs?._metadata
                                  ?.execution_duration_ms && (
                                  <div className="bg-background border rounded-md p-3">
                                    <div className="text-xs text-muted-foreground mb-1">
                                      执行时长
                                    </div>
                                    <div className="text-lg font-semibold font-mono">
                                      {formatDuration(
                                        log.outputs._metadata
                                          .execution_duration_ms,
                                      )}
                                    </div>
                                  </div>
                                )}

                                {log.outputs?._metadata?.memory_usage_mb !==
                                  undefined && (
                                  <div className="bg-background border rounded-md p-3">
                                    <div className="text-xs text-muted-foreground mb-1">
                                      内存使用
                                    </div>
                                    <div
                                      className={`text-lg font-semibold ${
                                        log.outputs._metadata.memory_usage_mb <
                                        0
                                          ? "text-green-600"
                                          : ""
                                      }`}
                                    >
                                      {log.outputs._metadata.memory_usage_mb > 0
                                        ? "+"
                                        : ""}
                                      {log.outputs._metadata.memory_usage_mb.toFixed(
                                        1,
                                      )}
                                      MB
                                    </div>
                                  </div>
                                )}

                                {log.outputs?._metadata?.data_metrics
                                  ?.row_count !== undefined && (
                                  <div className="bg-background border rounded-md p-3">
                                    <div className="text-xs text-muted-foreground mb-1">
                                      数据行数
                                    </div>
                                    <div className="text-lg font-semibold">
                                      {log.outputs._metadata.data_metrics.row_count.toLocaleString()}
                                    </div>
                                  </div>
                                )}

                                {log.outputs?._metadata?.data_metrics
                                  ?.field_count !== undefined &&
                                  log.outputs._metadata.data_metrics
                                    .field_count > 0 && (
                                    <div className="bg-background border rounded-md p-3">
                                      <div className="text-xs text-muted-foreground mb-1">
                                        字段数
                                      </div>
                                      <div className="text-lg font-semibold">
                                        {log.outputs._metadata.data_metrics.field_count.toLocaleString()}
                                      </div>
                                    </div>
                                  )}

                                {log.outputs?._metadata?.data_metrics
                                  ?.data_size !== undefined &&
                                  log.outputs._metadata.data_metrics.data_size >
                                    0 && (
                                    <div className="bg-background border rounded-md p-3">
                                      <div className="text-xs text-muted-foreground mb-1">
                                        数据大小
                                      </div>
                                      <div className="text-lg font-semibold">
                                        {(
                                          log.outputs._metadata.data_metrics
                                            .data_size / 1024
                                        ).toFixed(2)}{" "}
                                        KB
                                      </div>
                                    </div>
                                  )}

                                {log.outputs?._metadata?.llm_metrics
                                  ?.estimated_cost_usd && (
                                  <div className="bg-background border rounded-md p-3">
                                    <div className="text-xs text-muted-foreground mb-1">
                                      预估成本
                                    </div>
                                    <div className="text-lg font-semibold">
                                      $
                                      {log.outputs._metadata.llm_metrics.estimated_cost_usd.toFixed(
                                        4,
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* 输入输出元数据 */}
                              <div className="grid grid-cols-2 gap-4">
                                {/* 输入信息 */}
                                <div className="bg-background border rounded-md p-3">
                                  <div className="text-sm font-semibold mb-2 flex items-center gap-2">
                                    <IconComponent
                                      name="ArrowDownToLine"
                                      className="h-4 w-4"
                                    />
                                    输入信息
                                  </div>
                                  <pre className="text-xs font-mono bg-muted/30 p-2 rounded max-h-60 overflow-auto">
                                    {formatJSON(log.inputs?._metadata)}
                                  </pre>
                                </div>

                                {/* 输出信息 */}
                                <div className="bg-background border rounded-md p-3">
                                  <div className="text-sm font-semibold mb-2 flex items-center gap-2">
                                    <IconComponent
                                      name="ArrowUpFromLine"
                                      className="h-4 w-4"
                                    />
                                    输出信息
                                  </div>
                                  <pre className="text-xs font-mono bg-muted/30 p-2 rounded max-h-60 overflow-auto">
                                    {formatJSON(log.outputs?._metadata)}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
