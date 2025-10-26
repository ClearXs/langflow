"""ETL Field Rows Merge Component
多行合并为一行组件 - 将多行数据合并为一行
支持多种合并策略和自定义分隔符
"""

from typing import Any

import i18n
import pandas as pd
from pandas import DataFrame

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, IntInput, MessageTextInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data

# Delimiter constants
DELIMITER_COMMA = ","
DELIMITER_SEMICOLON = ";"
DELIMITER_TAB = "\\t"
DELIMITER_PIPE = "|"
DELIMITER_SPACE = "SPACE"  # Use special identifier to avoid UI issues with empty string
DELIMITER_NEWLINE = "\\n"
DELIMITER_CUSTOM = "custom"


class ETLFieldRowsMergeComponent(Component):
    """多行合并为一行组件 - 将多行数据合并为单行"""

    display_name = i18n.t("components.manipulations.field_rows_merge.display_name")
    description = i18n.t("components.manipulations.field_rows_merge.description")
    icon = "merge"
    name = "ETLFieldRowsMerge"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_rows_merge.data_input.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.data_input.info"),
            required=True,
        ),
        DropdownInput(
            name="merge_strategy",
            display_name=i18n.t("components.manipulations.field_rows_merge.merge_strategy.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.merge_strategy.info"),
            options=["keep_first", "keep_last", "merge_all", "sum", "mean", "max", "min", "concat"],
            options_metadata=[
                {
                    "value": "keep_first",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.keep_first"),
                },
                {
                    "value": "keep_last",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.keep_last"),
                },
                {
                    "value": "merge_all",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.merge_all"),
                },
                {
                    "value": "sum",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.sum"),
                },
                {
                    "value": "mean",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.mean"),
                },
                {
                    "value": "max",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.max"),
                },
                {
                    "value": "min",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.min"),
                },
                {
                    "value": "concat",
                    "label": i18n.t("components.manipulations.field_rows_merge.merge_strategy.concat"),
                },
            ],
            value="merge_all",
        ),
        DropdownInput(
            name="group_by",
            display_name=i18n.t("components.manipulations.field_rows_merge.group_by.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.group_by.info"),
            options=[],  # Will be loaded dynamically from data_input
            refresh_button=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="concat_separator",
            display_name=i18n.t("components.manipulations.field_rows_merge.concat_separator.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.concat_separator.info"),
            options=[
                DELIMITER_COMMA,
                DELIMITER_SEMICOLON,
                DELIMITER_TAB,
                DELIMITER_PIPE,
                DELIMITER_SPACE,
                DELIMITER_NEWLINE,
                DELIMITER_CUSTOM,
            ],
            options_metadata=[
                {
                    "value": DELIMITER_COMMA,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.comma"),
                },
                {
                    "value": DELIMITER_SEMICOLON,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.semicolon"),
                },
                {
                    "value": DELIMITER_TAB,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.tab"),
                },
                {
                    "value": DELIMITER_PIPE,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.pipe"),
                },
                {
                    "value": DELIMITER_SPACE,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.space"),
                },
                {
                    "value": DELIMITER_NEWLINE,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.newline"),
                },
                {
                    "value": DELIMITER_CUSTOM,
                    "label": i18n.t("components.manipulations.field_rows_merge.concat_separator.custom"),
                },
            ],
            value=DELIMITER_SEMICOLON,
        ),
        StrInput(
            name="custom_separator",
            display_name=i18n.t("components.manipulations.field_rows_merge.custom_separator.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.custom_separator.info"),
            value="",
            advanced=False,
        ),
        MessageTextInput(
            name="numeric_fields",
            display_name=i18n.t("components.manipulations.field_rows_merge.numeric_fields.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.numeric_fields.info"),
            placeholder="amount,quantity,price",
            advanced=True,
        ),
        MessageTextInput(
            name="exclude_fields",
            display_name=i18n.t("components.manipulations.field_rows_merge.exclude_fields.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.exclude_fields.info"),
            placeholder="id,timestamp",
            advanced=True,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t("components.manipulations.field_rows_merge.chunk_size.display_name"),
            info=i18n.t("components.manipulations.field_rows_merge.chunk_size.info"),
            value=100000,
            range_spec={"min": 1000, "max": 1000000},
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_rows_merge.outputs.data"),
            method="merge_rows",
        ),
        Output(
            name="fields_schema",
            display_name=i18n.t("components.manipulations.field_rows_merge.outputs.fields_schema"),
            method="get_fields_schema",
        ),
        Output(
            name="preview",
            display_name=i18n.t("components.manipulations.field_rows_merge.outputs.preview"),
            method="preview_result",
        ),
        Output(
            name="statistics",
            display_name=i18n.t("components.manipulations.field_rows_merge.outputs.statistics"),
            method="get_statistics",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates to load fields from upstream data."""
        logger.info(
            f"[FieldRowsMerge] update_build_config called - field_name: {field_name}, field_value: {field_value}, action: {action}"
        )

        # Load field options when refresh button is clicked
        if field_name == "group_by" and action == "refresh":
            logger.info("[FieldRowsMerge] Refresh button clicked - loading field options from upstream")
            try:
                # Get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data:
                    logger.warning("[FieldRowsMerge] No graph data available")
                    self.status = "No graph data available. Please ensure the component is connected to a data source."
                    return build_config

                # Get data sample from upstream node
                upstream_data = await self.get_upstream_data(
                    input_name="data_input", graph_data=graph_data, sample_size=1, vertex_id=node_id
                )

                if upstream_data:
                    # Extract field names
                    field_names = self._extract_field_names(upstream_data)
                    logger.debug(f"[FieldRowsMerge] Extracted {len(field_names)} fields: {field_names}")
                    if field_names:
                        build_config["group_by"]["options"] = field_names
                        self.status = f"Successfully loaded {len(field_names)} fields from upstream data source"
                        logger.info(f"[FieldRowsMerge] Successfully loaded {len(field_names)} field options")
                    else:
                        self.status = "No fields found in upstream data"
                        logger.warning("[FieldRowsMerge] No fields found in upstream data")
                else:
                    self.status = (
                        "No data available from upstream component. Please ensure it's connected and has data."
                    )
                    logger.warning("[FieldRowsMerge] No upstream data available")

            except ValueError as e:
                logger.warning(f"[FieldRowsMerge] Expected error loading fields: {e}")
                self.status = f"Failed to load fields: {e!s}"
            except Exception as e:
                logger.error(f"[FieldRowsMerge] Unexpected error loading field options: {e}", exc_info=True)
                self.status = f"Error loading fields: {e!s}"

        # Handle conditional display for custom_separator
        if field_name == "concat_separator":
            if field_value == DELIMITER_CUSTOM:
                if "custom_separator" in build_config:
                    build_config["custom_separator"]["show"] = True
            elif "custom_separator" in build_config:
                build_config["custom_separator"]["show"] = False

        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """从数据流中提取字段名列表"""
        if not data_list or len(data_list) == 0:
            return []

        first_record = data_list[0]
        if hasattr(first_record, "data") and isinstance(first_record.data, dict):
            return list(first_record.data.keys())
        if isinstance(first_record, dict):
            return list(first_record.keys())

        return []

    def _get_separator(self) -> str:
        """Get the actual separator to use"""
        if self.concat_separator == DELIMITER_CUSTOM:
            return getattr(self, "custom_separator", ";")
        if self.concat_separator == DELIMITER_TAB:
            return "\t"
        if self.concat_separator == DELIMITER_NEWLINE:
            return "\n"
        if self.concat_separator == DELIMITER_SPACE:
            return " "
        return self.concat_separator

    def _parse_field_list(self, field_value) -> list[str]:
        """解析字段列表 - 支持列表或逗号分隔字符串"""
        if isinstance(field_value, list):
            return field_value
        if not field_value:
            return []
        return [f.strip() for f in str(field_value).split(",") if f.strip()]

    def _merge_by_strategy(self, df: DataFrame) -> DataFrame:
        """根据策略执行合并"""
        if self.merge_strategy == "keep_first":
            return df.head(1)
        if self.merge_strategy == "keep_last":
            return df.tail(1)
        if self.merge_strategy == "merge_all" or self.merge_strategy == "concat":
            return self._merge_all_rows(df)
        if self.merge_strategy in ["sum", "mean", "max", "min"]:
            return self._aggregate_rows(df)
        return df.head(1)

    def _merge_all_rows(self, df: DataFrame) -> DataFrame:
        """合并所有行为一行"""
        # 解析要排除的字段
        exclude_fields = self._parse_field_list(self.exclude_fields)

        # Get actual separator
        separator = self._get_separator()

        # 创建合并后的字典
        merged_dict = {}

        for col in df.columns:
            if col in exclude_fields:
                # 排除的字段取第一个值
                merged_dict[col] = df[col].iloc[0] if len(df) > 0 else None
            else:
                # 将所有非空值连接起来
                non_null_values = df[col].dropna()
                if len(non_null_values) > 0:
                    # 转换为字符串并连接
                    merged_dict[col] = separator.join(str(v) for v in non_null_values)
                else:
                    merged_dict[col] = None

        return pd.DataFrame([merged_dict])

    def _aggregate_rows(self, df: DataFrame) -> DataFrame:
        """聚合行数据"""
        # 解析数值字段
        numeric_fields = self._parse_field_list(self.numeric_fields)
        exclude_fields = self._parse_field_list(self.exclude_fields)

        # Get actual separator
        separator = self._get_separator()

        # 自动检测数值字段
        if not numeric_fields:
            numeric_fields = df.select_dtypes(include=["number"]).columns.tolist()

        # 创建聚合字典
        agg_dict = {}

        for col in df.columns:
            if col in exclude_fields:
                # 排除的字段取第一个值
                agg_dict[col] = "first"
            elif col in numeric_fields:
                # 数值字段使用指定的聚合函数
                if self.merge_strategy == "sum":
                    agg_dict[col] = "sum"
                elif self.merge_strategy == "mean":
                    agg_dict[col] = "mean"
                elif self.merge_strategy == "max":
                    agg_dict[col] = "max"
                elif self.merge_strategy == "min":
                    agg_dict[col] = "min"
            else:
                # 非数值字段连接为字符串
                agg_dict[col] = lambda x: separator.join(str(v) for v in x.dropna())

        # 执行聚合
        result = df.agg(agg_dict).to_frame().T
        return result

    def _process_chunk(self, df_chunk: DataFrame) -> DataFrame:
        """处理单个数据块"""
        if self.group_by:
            # 按分组字段进行分组合并
            group_fields = self._parse_field_list(self.group_by)

            # 验证分组字段存在
            for field in group_fields:
                if field not in df_chunk.columns:
                    raise ValueError(
                        i18n.t("components.manipulations.field_rows_merge.errors.field_not_found", field=field)
                    )

            # 按组执行合并
            result_chunks = []
            for _, group_df in df_chunk.groupby(group_fields):
                merged_group = self._merge_by_strategy(group_df)
                result_chunks.append(merged_group)

            if result_chunks:
                return pd.concat(result_chunks, ignore_index=True)
            return pd.DataFrame()
        # 全局合并
        return self._merge_by_strategy(df_chunk)

    def merge_rows(self) -> list[Data]:
        """执行多行合并为一行操作"""
        try:
            self.status = i18n.t("components.manipulations.field_rows_merge.status.merging")
            logger.info(f"[FieldRowsMerge] Starting merge operation with strategy: {self.merge_strategy}")

            if not self.data_input:
                raise ValueError(i18n.t("components.manipulations.field_rows_merge.errors.no_input_data"))

            # 转换为DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])
            total_rows = len(df)
            logger.info(f"[FieldRowsMerge] Processing {total_rows} rows")

            # 对于大数据量且有分组的情况，分块处理
            if total_rows > self.chunk_size and self.group_by:
                logger.info(f"[FieldRowsMerge] Large dataset with grouping, processing in chunks of {self.chunk_size}")
                chunks = []
                for start in range(0, total_rows, self.chunk_size):
                    end = min(start + self.chunk_size, total_rows)
                    df_chunk = df.iloc[start:end]
                    processed_chunk = self._process_chunk(df_chunk)
                    chunks.append(processed_chunk)
                    logger.debug(f"[FieldRowsMerge] Processed chunk {start}-{end}")

                df_result = pd.concat(chunks, ignore_index=True)
            else:
                df_result = self._process_chunk(df)

            # 转换回Data对象列表
            result = [Data(data=row.to_dict()) for _, row in df_result.iterrows()]

            self.status = i18n.t(
                "components.manipulations.field_rows_merge.status.success", original=total_rows, result=len(result)
            )
            logger.info(f"[FieldRowsMerge] Merge completed: {total_rows} rows -> {len(result)} rows")

            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_rows_merge.errors.merge_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[FieldRowsMerge] Merge failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def preview_result(self) -> Data:
        """预览合并结果"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_rows_merge.errors.no_input_data")})

            # 取前1000条数据进行预览
            preview_data = self.data_input[:1000]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in preview_data])

            # 执行合并预览
            df_preview = self._process_chunk(df.head(100))

            # 计算合并比例
            merge_ratio = len(df) / len(df_preview) if len(df_preview) > 0 else 0

            return Data(
                data={
                    "original_rows": len(df),
                    "preview_rows": len(df_preview),
                    "merge_ratio": merge_ratio,
                    "merge_strategy": self.merge_strategy,
                    "group_by": self.group_by,
                    "concat_separator": self.concat_separator,
                    "columns": list(df_preview.columns),
                    "sample_data": df_preview.head(20).to_dict("records"),
                }
            )

        except Exception as e:
            logger.error(f"[FieldRowsMerge] Preview failed: {e}")
            return Data(data={"error": str(e)})

    def get_statistics(self) -> Data:
        """获取合并统计信息"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_rows_merge.errors.no_input_data")})

            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            stats = {
                "total_input_rows": len(df),
                "total_columns": len(df.columns),
                "merge_strategy": self.merge_strategy,
            }

            # 如果有分组字段，统计分组信息
            if self.group_by:
                group_fields = self._parse_field_list(self.group_by)
                if all(field in df.columns for field in group_fields):
                    group_sizes = df.groupby(group_fields).size()
                    stats.update(
                        {
                            "group_fields": group_fields,
                            "unique_groups": len(group_sizes),
                            "avg_rows_per_group": group_sizes.mean(),
                            "max_rows_per_group": group_sizes.max(),
                            "min_rows_per_group": group_sizes.min(),
                            "estimated_output_rows": len(group_sizes),
                        }
                    )
            else:
                stats["estimated_output_rows"] = 1

            # 数值字段统计
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            stats["numeric_fields_count"] = len(numeric_cols)
            stats["text_fields_count"] = len(df.columns) - len(numeric_cols)

            # 空值统计
            null_counts = df.isnull().sum()
            stats.update(
                {
                    "total_null_values": null_counts.sum(),
                    "avg_nulls_per_column": null_counts.mean(),
                }
            )

            return Data(data=stats)

        except Exception as e:
            logger.error(f"[FieldRowsMerge] Statistics failed: {e}")
            return Data(data={"error": str(e)})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the merge result.

        Returns:
            Data: A Data object containing fields metadata
        """
        try:
            logger.info("[FieldRowsMerge] get_fields_schema called")

            if not self.data_input:
                return Data(data={"fields": [], "field_names": []})

            # Get sample data to infer schema
            sample_data = self.data_input[:10]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in sample_data])

            if df.empty:
                return Data(data={"fields": [], "field_names": []})

            # Process sample to get result schema
            df_result = self._process_chunk(df)

            fields = []
            for col in df_result.columns:
                dtype = df_result[col].dtype
                if pd.api.types.is_integer_dtype(dtype):
                    data_type = "integer"
                elif pd.api.types.is_float_dtype(dtype):
                    data_type = "float"
                elif pd.api.types.is_bool_dtype(dtype):
                    data_type = "boolean"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    data_type = "datetime"
                else:
                    data_type = "string"

                fields.append({"name": col, "type": data_type})

            field_names = [f["name"] for f in fields]

            logger.info(f"[FieldRowsMerge] Returning schema with {len(fields)} fields")
            return Data(data={"fields": fields, "field_names": field_names})

        except Exception as e:
            logger.error(f"[FieldRowsMerge] Failed to get fields schema: {e}")
            return Data(data={"fields": [], "field_names": []})
