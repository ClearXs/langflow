/**
 * Data exchange types for component interaction tracking
 */

export interface DataExchangeRecord {
  id: string;
  timestamp: string;
  transaction_id: string;
  source_vertex_id: string;
  target_vertex_id: string;
  exchange_type: "direct" | "broadcast" | "conditional" | "aggregated";
  data_type: string;
  data_size: number;
  data_sample?: Record<string, any>;
  exchange_metadata?: {
    source_component?: string;
    target_component?: string;
    [key: string]: any;
  };
}

export interface DataExchangeStats {
  total_exchanges: number;
  total_data_size: number;
  unique_source_vertices: number;
  unique_target_vertices: number;
  exchange_by_type: Record<string, number>;
  avg_data_size: number;
}

export interface VertexExchange {
  vertex_id: string;
  input_exchanges: DataExchangeRecord[];
  output_exchanges: DataExchangeRecord[];
  total_input_count: number;
  total_output_count: number;
  total_input_size: number;
  total_output_size: number;
}

export interface DataExchangeQueryParams {
  flow_id: string;
  source_vertex_id?: string;
  target_vertex_id?: string;
  exchange_type?: string;
  limit?: number;
}
