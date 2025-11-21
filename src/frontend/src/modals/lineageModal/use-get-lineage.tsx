import { useQuery } from "@tanstack/react-query";
import { api } from "@/controllers/API/api";

export interface LineageTable {
  id: string;
  node_id: string;
  node_type: string;
  node_name: string;
  datasource_id?: string;
  datasource_name?: string;
  table_name: string;
  type: "source" | "target";
  fields?: Array<{
    name: string;
    type: string;
    is_key: boolean;
    source_field?: string;
  }>;
}

export interface LineageRelationship {
  id: string;
  source_table_id: string;
  source_table_name: string;
  target_table_id: string;
  target_table_name: string;
  transformation_path: Array<{
    id: string;
    type: string;
    name: string;
  }>;
  field_mappings: Array<{
    source_field: string;
    target_field: string;
    source_type: string;
    target_type: string;
    transformations: string[];
  }>;
}

export interface LineageData {
  flow_id: string;
  flow_name: string;
  flow_description?: string;
  tables: LineageTable[];
  relationships: LineageRelationship[];
  total_tables: number;
  total_relationships: number;
}

export const useGetLineage = (flowId: string, tableName?: string) => {
  return useQuery<LineageData>({
    queryKey: ["lineage", flowId, tableName],
    queryFn: async () => {
      const params = tableName
        ? `?table_name=${encodeURIComponent(tableName)}`
        : "";
      const response = await api.get(
        `/api/v1/flows/${flowId}/lineage${params}`,
      );
      return response.data;
    },
    enabled: !!flowId,
    refetchOnWindowFocus: false,
  });
};

export const useGetTables = (flowId: string) => {
  return useQuery({
    queryKey: ["lineage-tables", flowId],
    queryFn: async () => {
      const response = await api.get(`/api/v1/flows/${flowId}/lineage/tables`);
      return response.data;
    },
    enabled: !!flowId,
    refetchOnWindowFocus: false,
  });
};
