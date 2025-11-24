"""ETL Field Pivot Component
多行转换为多列组件 - 将行数据转换为列（pivot操作）
支持分组、聚合和大数据量处理
"""

from typing import Any

import i18n
import pandas as pd
from pandas import DataFrame

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, IntInput, MessageTextInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFieldPivotComponent(Component):
    """多行转换为多列组件 - 执行pivot操作"""

    display_name = i18n.t("components.manipulations.field_pivot.display_name")
    description = i18n.t("components.manipulations.field_pivot.description")
    icon = "table-properties"
    name = "ETLFieldPivot"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_pivot.data_input.display_name"),
            info=i18n.t("components.manipulations.field_pivot.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="group_fields",
            display_name=i18n.t("components.manipulations.field_pivot.group_fields.display_name"),
            info=i18n.t("components.manipulations.field_pivot.group_fields.info"),
            options=[],  # Will be loaded dynamically from data_input
            refresh_button=True,
            real_time_refresh=True,
            required=True,
        ),
        DropdownInput(
            name="key_field",
            display_name=i18n.t("components.manipulations.field_pivot.key_field.display_name"),
            info=i18n.t("components.manipulations.field_pivot.key_field.info"),
            options=[],  # Will be loaded dynamically from data_input
            refresh_button=True,
            real_time_refresh=True,
            required=True,
        ),
        DropdownInput(
            name="value_field",
            display_name=i18n.t("components.manipulations.field_pivot.value_field.display_name"),
            info=i18n.t("components.manipulations.field_pivot.value_field.info"),
            options=[],  # Will be loaded dynamically from data_input
            refresh_button=True,
            real_time_refresh=True,
            required=True,
        ),
        DropdownInput(
            name="agg_function",
            display_name=i18n.t("components.manipulations.field_pivot.agg_function.display_name"),
            info=i18n.t("components.manipulations.field_pivot.agg_function.info"),
            options=["first", "last", "sum", "mean", "max", "min", "count", "concat"],
            options_metadata=[
                {
                    "value": "first",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.first"),
                },
                {
                    "value": "last",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.last"),
                },
                {
                    "value": "sum",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.sum"),
                },
                {
                    "value": "mean",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.mean"),
                },
                {
                    "value": "max",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.max"),
                },
                {
                    "value": "min",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.min"),
                },
                {
                    "value": "count",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.count"),
                },
                {
                    "value": "concat",
                    "label": i18n.t("components.manipulations.field_pivot.agg_function.concat"),
                },
            ],
            value="first",
        ),
        MessageTextInput(
            name="concat_separator",
            display_name=i18n.t("components.manipulations.field_pivot.concat_separator.display_name"),
            info=i18n.t("components.manipulations.field_pivot.concat_separator.info"),
            value=",",
            advanced=True,
        ),
        TableInput(
            name="target_field_mapping",
            display_name=i18n.t("components.manipulations.field_pivot.target_field_mapping.display_name"),
            info=i18n.t("components.manipulations.field_pivot.target_field_mapping.info"),
            table_schema=[
                {
                    "name": "key_value",
                    "display_name": i18n.t("components.manipulations.field_pivot.target_field_mapping.key_value"),
                    "type": "str",
                },
                {
                    "name": "target_field",
                    "display_name": i18n.t("components.manipulations.field_pivot.target_field_mapping.target_field"),
                    "type": "str",
                },
            ],
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
            },
        ),
        MessageTextInput(
            name="fill_value",
            display_name=i18n.t("components.manipulations.field_pivot.fill_value.display_name"),
            info=i18n.t("components.manipulations.field_pivot.fill_value.info"),
            value="",
            advanced=True,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t("components.manipulations.field_pivot.chunk_size.display_name"),
            info=i18n.t("components.manipulations.field_pivot.chunk_size.info"),
            value=100000,
            range_spec={"min": 1000, "max": 1000000},
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data", display_name=i18n.t("components.manipulations.field_pivot.outputs.data"), method="pivot_rows"
        ),
        Output(
            name="fields_schema",
            display_name=i18n.t("components.manipulations.field_pivot.outputs.fields_schema"),
            method="get_fields_schema",
        ),
        Output(
            name="preview",
            display_name=i18n.t("components.manipulations.field_pivot.outputs.preview"),
            method="preview_result",
        ),
        Output(
            name="statistics",
            display_name=i18n.t("components.manipulations.field_pivot.outputs.statistics"),
            method="get_statistics",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates to load fields from upstream data."""
        logger.info(
            f"[FieldPivot] update_build_config called - field_name: {field_name}, field_value: {field_value}, action: {action}"
        )

        # Load field options when refresh button is clicked on any of the field dropdowns
        if field_name in ["group_fields", "key_field", "value_field"] and action == "refresh":
            logger.info(f"[FieldPivot] Refresh button clicked on {field_name} - loading field options from upstream")
            try:
                # Get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data:
                    logger.warning("[FieldPivot] No graph data available")
                    self.status = "No graph data available. Please ensure the component is connected to a data source."
                    return build_config

                field_names = []

                # Primary strategy: Try to execute upstream node to get actual data
                try:
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input", graph_data=graph_data, sample_size=1, vertex_id=node_id
                    )

                    if upstream_data:
                        # Extract field names
                        field_names = self._extract_field_names(upstream_data)
                        logger.debug(
                            f"[FieldPivot] Extracted {len(field_names)} fields from upstream data: {field_names}"
                        )
                    else:
                        logger.warning("[FieldPivot] No data returned from upstream node")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configuration
                    logger.warning(f"[FieldPivot] Upstream execution failed: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        fields = find_and_extract_upstream_fields(graph_data, node_id, "data_input", "FieldPivot")

                        if fields:
                            field_names = [field["name"] for field in fields]
                            logger.info(f"[FieldPivot] Extracted {len(field_names)} fields from static config")
                        else:
                            logger.warning("[FieldPivot] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[FieldPivot] Static analysis also failed")

                # Update build_config with results
                if field_names:
                    # Update all three field dropdowns
                    build_config["group_fields"]["options"] = field_names
                    build_config["key_field"]["options"] = field_names
                    build_config["value_field"]["options"] = field_names
                    self.status = f"Successfully loaded {len(field_names)} fields from upstream data source"
                    logger.info(f"[FieldPivot] Successfully loaded {len(field_names)} field options")
                else:
                    self.status = "Unable to automatically load fields, please configure manually"
                    logger.warning("[FieldPivot] No fields could be extracted")

            except Exception as e:  # noqa: BLE001
                logger.error(f"[FieldPivot] Unexpected error loading field options: {e}", exc_info=True)
                self.status = f"Error loading fields: {e!s}"

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

    def _custom_concat(self, x):
        """自定义连接聚合函数"""
        if len(x) == 0:
            return self.fill_value or ""
        return self.concat_separator.join(str(v) for v in x if pd.notna(v))

    def _get_agg_func(self):
        """获取聚合函数"""
        if self.agg_function == "concat":
            return self._custom_concat
        if self.agg_function == "first":
            return "first"
        if self.agg_function == "last":
            return "last"
        if self.agg_function == "sum":
            return "sum"
        if self.agg_function == "mean":
            return "mean"
        if self.agg_function == "max":
            return "max"
        if self.agg_function == "min":
            return "min"
        if self.agg_function == "count":
            return "count"
        return "first"

    def _process_chunk(self, df_chunk: DataFrame) -> DataFrame:
        """处理单个数据块"""
        # 解析分组字段 - now it's a list from dropdown
        if isinstance(self.group_fields, list):
            group_fields = self.group_fields
        else:
            # Fallback for comma-separated string
            group_fields = [f.strip() for f in str(self.group_fields).split(",") if f.strip()]

        # 验证字段存在
        for field in group_fields:
            if field not in df_chunk.columns:
                raise ValueError(i18n.t("components.manipulations.field_pivot.errors.field_not_found", field=field))

        if self.key_field not in df_chunk.columns:
            raise ValueError(
                i18n.t("components.manipulations.field_pivot.errors.field_not_found", field=self.key_field)
            )

        if self.value_field not in df_chunk.columns:
            raise ValueError(
                i18n.t("components.manipulations.field_pivot.errors.field_not_found", field=self.value_field)
            )

        # 获取聚合函数
        agg_func = self._get_agg_func()

        # 执行pivot操作
        try:
            pivoted = df_chunk.pivot_table(
                index=group_fields,
                columns=self.key_field,
                values=self.value_field,
                aggfunc=agg_func,
                fill_value=self.fill_value if self.fill_value else None,
            )

            # 重置索引
            pivoted = pivoted.reset_index()

            # 应用字段映射
            if self.target_field_mapping:
                rename_map = {m["key_value"]: m["target_field"] for m in self.target_field_mapping}
                pivoted = pivoted.rename(columns=rename_map)

            # 展平多级列索引（如果存在）
            if isinstance(pivoted.columns, pd.MultiIndex):
                pivoted.columns = ["_".join(str(col) for col in cols if col) for cols in pivoted.columns]

        except Exception as e:
            logger.error(f"[FieldPivot] Pivot operation failed: {e}")
            raise ValueError(i18n.t("components.manipulations.field_pivot.errors.pivot_failed", error=str(e)))

        return pivoted

    def pivot_rows(self) -> list[Data]:
        """执行多行转换为多列操作"""
        try:
            self.status = i18n.t("components.manipulations.field_pivot.status.pivoting")
            logger.info("[FieldPivot] Starting pivot operation")

            if not self.data_input:
                raise ValueError(i18n.t("components.manipulations.field_pivot.errors.no_input_data"))

            # 转换为DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])
            total_rows = len(df)
            logger.info(f"[FieldPivot] Processing {total_rows} rows")

            # 对于pivot操作，通常需要整体处理而不是分块
            # 因为pivot需要看到所有相关的数据才能正确聚合
            if total_rows > self.chunk_size * 10:
                logger.warning(f"[FieldPivot] Large dataset ({total_rows} rows) may cause memory issues during pivot")

            # 执行pivot
            df_result = self._process_chunk(df)

            # 转换回Data对象列表
            result = [Data(data=row.to_dict()) for _, row in df_result.iterrows()]

            self.status = i18n.t(
                "components.manipulations.field_pivot.status.success", original=total_rows, result=len(result)
            )
            logger.info(
                f"[FieldPivot] Pivot completed: {total_rows} rows -> {len(result)} rows, {len(df_result.columns)} columns"
            )

            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_pivot.errors.pivot_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[FieldPivot] Pivot failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def preview_result(self) -> Data:
        """预览pivot结果"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_pivot.errors.no_input_data")})

            # 取前1000条数据进行预览
            preview_data = self.data_input[:1000]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in preview_data])

            # 执行pivot预览
            df_preview = self._process_chunk(df)

            # 获取唯一键值
            unique_keys = df[self.key_field].unique() if self.key_field in df.columns else []

            return Data(
                data={
                    "original_rows": len(df),
                    "preview_rows": len(df_preview),
                    "original_columns": list(df.columns),
                    "result_columns": list(df_preview.columns),
                    "unique_key_values": list(unique_keys)[:20],  # 最多显示20个
                    "unique_key_count": len(unique_keys),
                    "group_fields": self.group_fields,
                    "key_field": self.key_field,
                    "value_field": self.value_field,
                    "agg_function": self.agg_function,
                    "sample_data": df_preview.head(20).to_dict("records"),
                }
            )

        except Exception as e:
            logger.error(f"[FieldPivot] Preview failed: {e}")
            return Data(data={"error": str(e)})

    def get_statistics(self) -> Data:
        """获取pivot统计信息"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_pivot.errors.no_input_data")})

            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            # 解析分组字段
            if isinstance(self.group_fields, list):
                group_fields = self.group_fields
            else:
                group_fields = [f.strip() for f in str(self.group_fields).split(",") if f.strip()]

            stats = {
                "total_input_rows": len(df),
                "total_columns": len(df.columns),
                "group_fields": group_fields,
                "group_fields_count": len(group_fields),
                "key_field": self.key_field,
                "value_field": self.value_field,
                "agg_function": self.agg_function,
            }

            # 统计唯一值
            if self.key_field in df.columns:
                unique_keys = df[self.key_field].unique()
                stats["unique_key_values_count"] = len(unique_keys)
                stats["estimated_new_columns"] = len(unique_keys)

            # 统计分组数量
            if all(field in df.columns for field in group_fields):
                group_count = df.groupby(group_fields).size().shape[0]
                stats["unique_groups"] = group_count
                stats["estimated_output_rows"] = group_count

            # 统计值字段的信息
            if self.value_field in df.columns:
                value_series = df[self.value_field]
                stats.update(
                    {
                        "value_field_nulls": value_series.isna().sum(),
                        "value_field_non_nulls": value_series.notna().sum(),
                    }
                )

                # 如果是数值类型，添加统计信息
                if pd.api.types.is_numeric_dtype(value_series):
                    stats.update(
                        {
                            "value_field_min": value_series.min(),
                            "value_field_max": value_series.max(),
                            "value_field_mean": value_series.mean(),
                        }
                    )

            return Data(data=stats)

        except Exception as e:
            logger.error(f"[FieldPivot] Statistics failed: {e}")
            return Data(data={"error": str(e)})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the pivot result.

        Returns:
            Data: A Data object containing fields metadata
        """
        try:
            logger.info("[FieldPivot] get_fields_schema called")

            if not self.data_input:
                return Data(data={"fields": [], "field_names": []})

            # Get sample data to infer schema
            sample_data = self.data_input[:10]  # Need more data for pivot
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

            logger.info(f"[FieldPivot] Returning schema with {len(fields)} fields")
            return Data(data={"fields": fields, "field_names": field_names})

        except Exception as e:
            logger.error(f"[FieldPivot] Failed to get fields schema: {e}")
            return Data(data={"fields": [], "field_names": []})
