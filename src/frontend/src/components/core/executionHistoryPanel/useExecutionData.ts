import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "@/controllers/API/api";
import useFlowStore from "@/stores/flowStore";
import useFlowsManagerStore from "@/stores/flowsManagerStore";

export interface ExecutionOutput {
  name: string;
  label: string;
  data: any;
}

interface Transaction {
  id: string;
  vertex_id: string;
  status: string;
  timestamp: string;
  inputs: Record<string, any> | null;
  outputs: Record<string, any> | null;
  error: string | null;
}

export function useExecutionData(
  nodeId: string | null,
  viewMode: "results" | "all" = "results",
) {
  const flowPool = useFlowStore((state) => state.flowPool);
  const currentFlowId = useFlowsManagerStore((state) => state.currentFlowId);

  // 从后端获取 transactions 数据
  const { data: transactionsData, refetch } = useQuery({
    queryKey: ["transactions", currentFlowId, nodeId],
    queryFn: async () => {
      if (!currentFlowId || !nodeId) return null;

      try {
        const response = await api.get<{ items: Transaction[] }>(
          "/api/v1/monitor/transactions",
          {
            params: {
              flow_id: currentFlowId,
              page: 1,
              size: 100, // 获取最近的100条，然后在前端过滤
            },
          },
        );

        // 在前端过滤出当前节点的 transactions
        if (response.data?.items) {
          const filteredItems = response.data.items
            .filter((tx) => tx.vertex_id === nodeId)
            .sort((a, b) => {
              // 按时间戳降序排序，确保最新的在前面
              return (
                new Date(b.timestamp).getTime() -
                new Date(a.timestamp).getTime()
              );
            });

          return {
            items: filteredItems.slice(0, 1), // 只取最新的一条
          };
        }

        return response.data;
      } catch (error) {
        console.error("Failed to fetch transactions:", error);
        return null;
      }
    },
    enabled: !!currentFlowId && !!nodeId,
    staleTime: 0, // 数据立即过期
    gcTime: 0, // 不缓存，立即垃圾回收
    refetchInterval: 5000, // 每5秒自动刷新一次
    refetchOnWindowFocus: true, // 窗口重新获得焦点时刷新
    refetchOnMount: true, // 组件挂载时刷新
  });

  return useMemo(() => {
    const outputs: ExecutionOutput[] = [];
    let latestBuild: any = null;
    let rawTransaction: Transaction | null = null;

    // 优先从 transactions 获取数据
    if (transactionsData?.items && transactionsData.items.length > 0) {
      const latestTransaction = transactionsData.items[0];
      rawTransaction = latestTransaction;

      // "all" 模式：显示所有数据（包括 artifacts, _metadata 等）
      if (viewMode === "all" && latestTransaction.outputs) {
        // 将整个 transaction.outputs 对象展示（包括所有字段）
        outputs.push({
          name: "all_data",
          label: "All Transaction Data",
          data: latestTransaction.outputs, // 直接使用 outputs 对象
        });
      }
      // "results" 模式：只显示 results.data
      else if (latestTransaction.outputs) {
        const transactionOutputs = latestTransaction.outputs;

        // 检查是否有 results.data 结构
        if ((transactionOutputs as any).results?.data) {
          const resultData = (transactionOutputs as any).results.data;

          if (Array.isArray(resultData)) {
            const parsedData = resultData.map((item: any) => {
              if (typeof item === "string") {
                try {
                  const parsed = JSON.parse(item);
                  return parsed;
                } catch {
                  return { value: item };
                }
              }
              return item;
            });

            outputs.push({
              name: "data",
              label: "Data",
              data: parsedData,
            });
          }
        }
        // 检查其他可能的输出格式
        else if ((transactionOutputs as any).data) {
          outputs.push({
            name: "data",
            label: "Data",
            data: (transactionOutputs as any).data,
          });
        }
      }
    }

    // 如果 transactions 没有数据，回退到 flowPool
    if (outputs.length === 0 && nodeId && flowPool[nodeId]) {
      const builds = flowPool[nodeId];
      if (builds.length > 0) {
        latestBuild = builds[builds.length - 1];

        // 检查 data.artifacts
        if (latestBuild.data?.artifacts) {
          const artifacts = latestBuild.data.artifacts;

          if (Array.isArray(artifacts)) {
            const artifactData = artifacts.map(
              (artifact: any) => artifact.data,
            );
            outputs.push({
              name: "artifacts",
              label: "Data",
              data: artifactData,
            });
          } else if (artifacts.data) {
            outputs.push({
              name: "artifacts",
              label: "Data",
              data: artifacts.data,
            });
          }
        }

        // 检查 data.results
        if (outputs.length === 0 && latestBuild.data?.results) {
          Object.entries(latestBuild.data.results).forEach(
            ([key, value]: [string, any]) => {
              if (value) {
                outputs.push({
                  name: key,
                  label: key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase()),
                  data: value,
                });
              }
            },
          );
        }
      }
    }

    return { outputs, latestBuild, rawTransaction };
  }, [transactionsData, nodeId, flowPool, viewMode]);
}
