from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, IntInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFieldValueMergeComponent(Component):
    display_name = i18n.t("components.manipulations.field_value_merge.display_name")
    description = i18n.t("components.manipulations.field_value_merge.description")
    icon = "git-merge"
    name = "ETLFieldValueMerge"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_value_merge.data_input.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="merge_configs",
            display_name=i18n.t("components.manipulations.field_value_merge.merge_configs.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.merge_configs.info"),
            table_schema=[
                {
                    "name": "new_field",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.new_field"),
                    "type": "str",
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.new_field_desc"),
                },
                {
                    "name": "operation",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.operation"),
                    "type": "str",
                    "options": ["A LINK B", "A + B", "A - B", "A * B", "A / B", "A % B"],
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.operation_desc"),
                },
                {
                    "name": "field_a",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.field_a"),
                    "type": "str",
                    "options": [],  # 动态加载
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.field_a_desc"),
                },
                {
                    "name": "field_b",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.field_b"),
                    "type": "str",
                    "options": [],  # 动态加载
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.field_b_desc"),
                },
                {
                    "name": "separator",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.separator"),
                    "type": "str",
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.separator_desc"),
                },
                {
                    "name": "value_type",
                    "display_name": i18n.t("components.manipulations.field_value_merge.merge_configs.value_type"),
                    "type": "str",
                    "options": ["string", "integer", "float", "boolean"],
                    "description": i18n.t("components.manipulations.field_value_merge.merge_configs.value_type_desc"),
                },
            ],
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.manipulations.field_value_merge.merge_configs.load_fields_button"),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
            required=True,
        ),
        IntInput(
            name="decimal_precision",
            display_name=i18n.t("components.manipulations.field_value_merge.decimal_precision.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.decimal_precision.info"),
            value=2,
            range_spec={"min": 0, "max": 10},
            advanced=True,
        ),
        BoolInput(
            name="drop_source_fields",
            display_name=i18n.t("components.manipulations.field_value_merge.drop_source_fields.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.drop_source_fields.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_value_merge.outputs.data"),
            method="merge_field_values",
        ),
        Output(
            name="field_preview",
            display_name=i18n.t("components.manipulations.field_value_merge.outputs.field_preview"),
            method="preview_fields",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """动态加载上游节点的字段列表"""
        logger.info(f"[FieldValueMerge] update_build_config called - field_name: {field_name}, action: {action}")

        # 当点击"加载字段列表"按钮时
        if field_name == "merge_configs" and action == "load_fields":
            try:
                # Try to get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        # PlaceholderGraph - no data available
                        logger.warning("[FieldValueMerge] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[FieldValueMerge] No graph data available")
                    self.status = i18n.t("components.manipulations.field_value_merge.errors.no_graph_data")
                    return build_config

                # 从上游节点获取数据样本
                upstream_data = await self.get_upstream_data(
                    input_name="data_input", graph_data=graph_data, sample_size=1, vertex_id=node_id
                )

                if upstream_data:
                    # 提取字段列表
                    fields = self._extract_field_names(upstream_data)

                    if fields:
                        # 1. 更新字段A和字段B的下拉选项
                        build_config["merge_configs"]["table_schema"][2]["options"] = fields  # field_a
                        build_config["merge_configs"]["table_schema"][3]["options"] = fields  # field_b

                        # 2. 自动填充表格数据（如果当前为空）
                        if not build_config["merge_configs"].get("value"):
                            # 创建一个示例行，让用户知道如何配置
                            default_row = {
                                "new_field": "merged_field",
                                "operation": "A LINK B",
                                "field_a": fields[0] if fields else "",
                                "field_b": fields[1] if len(fields) > 1 else fields[0] if fields else "",
                                "separator": "-",
                                "value_type": "string",
                            }
                            build_config["merge_configs"]["value"] = [default_row]

                        self.status = i18n.t(
                            "components.manipulations.field_value_merge.status.fields_loaded", count=len(fields)
                        )
                        logger.info(f"[FieldValueMerge] Loaded {len(fields)} fields: {fields}")
                    else:
                        self.status = i18n.t("components.manipulations.field_value_merge.status.no_fields_found")
                else:
                    self.status = i18n.t("components.manipulations.field_value_merge.status.no_fields_found")

            except ValueError as e:
                logger.warning(f"[FieldValueMerge] Field loading warning: {e}")
                self.status = i18n.t(
                    "components.manipulations.field_value_merge.errors.load_fields_failed", error=str(e)
                )
            except Exception as e:
                logger.error(f"[FieldValueMerge] Failed to load fields: {e}", exc_info=True)
                self.status = i18n.t(
                    "components.manipulations.field_value_merge.errors.load_fields_failed", error=str(e)
                )

        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """从数据流中提取字段名列表"""
        if not data_list or len(data_list) == 0:
            return []

        # 取第一条数据获取字段
        first_record = data_list[0]
        if hasattr(first_record, "data") and isinstance(first_record.data, dict):
            return list(first_record.data.keys())
        if isinstance(first_record, dict):
            return list(first_record.keys())

        return []

    def merge_field_values(self) -> list[Data]:
        """执行字段值合并操作"""
        try:
            self.status = i18n.t("components.manipulations.field_value_merge.status.merging")
            logger.info("[FieldValueMerge] Starting merge operation")

            if not self.data_input or not self.merge_configs:
                raise ValueError(i18n.t("components.manipulations.field_value_merge.errors.missing_config"))

            # Ensure data_input is a list
            if not isinstance(self.data_input, list):
                data_input_list = [self.data_input]
            else:
                data_input_list = self.data_input

            # Extract data from Data objects
            data_records = []
            for d in data_input_list:
                if hasattr(d, "data"):
                    # Handle Data objects
                    if isinstance(d.data, dict):
                        # Data object with dict payload
                        data_records.append(d.data)
                    elif isinstance(d.data, list):
                        # Data object with list payload - extend with all items
                        for item in d.data:
                            if isinstance(item, dict):
                                data_records.append(item)
                            else:
                                logger.warning(f"[FieldValueMerge] Skipping non-dict item in Data.data list: {type(item)}")
                    else:
                        logger.warning(f"[FieldValueMerge] Unknown Data.data type {type(d.data)}: {d.data}")
                elif isinstance(d, dict):
                    data_records.append(d)
                else:
                    logger.warning(f"[FieldValueMerge] Unexpected data type: {type(d)}, skipping")

            if not data_records:
                raise ValueError(i18n.t("components.manipulations.field_value_merge.errors.no_valid_data"))

            df = pd.DataFrame(data_records)

            # Normalize column names to strings to handle non-string column names
            df.columns = [str(col).strip() if isinstance(col, str) else str(col) for col in df.columns]

            logger.debug(f"[FieldValueMerge] Input dataframe: {len(df)} records, {len(df.columns)} fields")
            logger.debug(f"[FieldValueMerge] DataFrame columns: {list(df.columns)}")

            for idx, config in enumerate(self.merge_configs):
                new_field = config.get("new_field")
                operation = config.get("operation", "A LINK B")
                field_a = config.get("field_a")
                field_b = config.get("field_b")
                separator = config.get("separator", "")
                value_type = config.get("value_type", "string")

                logger.debug(
                    f"[FieldValueMerge] Config {idx + 1}: {new_field} = {field_a} {operation} {field_b} (type: {value_type})"
                )

                # 验证配置完整性
                if not new_field or not field_a or not field_b:
                    logger.warning(f"[FieldValueMerge] Config {idx + 1} incomplete, skipping")
                    continue

                # 验证字段存在
                if field_a not in df.columns:
                    raise ValueError(
                        i18n.t("components.manipulations.field_value_merge.errors.field_not_found", field=field_a)
                    )
                if field_b not in df.columns:
                    raise ValueError(
                        i18n.t("components.manipulations.field_value_merge.errors.field_not_found", field=field_b)
                    )

                # 执行计算
                if operation == "A LINK B":
                    # 字符串连接
                    df[new_field] = df[field_a].astype(str) + separator + df[field_b].astype(str)
                elif operation == "A + B":
                    df[new_field] = pd.to_numeric(df[field_a], errors="coerce") + pd.to_numeric(
                        df[field_b], errors="coerce"
                    )
                elif operation == "A - B":
                    df[new_field] = pd.to_numeric(df[field_a], errors="coerce") - pd.to_numeric(
                        df[field_b], errors="coerce"
                    )
                elif operation == "A * B":
                    df[new_field] = pd.to_numeric(df[field_a], errors="coerce") * pd.to_numeric(
                        df[field_b], errors="coerce"
                    )
                elif operation == "A / B":
                    df[new_field] = pd.to_numeric(df[field_a], errors="coerce") / pd.to_numeric(
                        df[field_b], errors="coerce"
                    )
                elif operation == "A % B":
                    df[new_field] = pd.to_numeric(df[field_a], errors="coerce") % pd.to_numeric(
                        df[field_b], errors="coerce"
                    )
                else:
                    logger.warning(f"[FieldValueMerge] Unknown operation: {operation}, treating as A LINK B")
                    df[new_field] = df[field_a].astype(str) + separator + df[field_b].astype(str)

                # 类型转换
                df[new_field] = self._convert_value_type(df[new_field], value_type, self.decimal_precision)

                # 删除源字段
                if self.drop_source_fields:
                    df = df.drop(columns=[field_a, field_b], errors="ignore")
                    logger.debug(f"[FieldValueMerge] Dropped source fields: {field_a}, {field_b}")

            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t("components.manipulations.field_value_merge.status.success", count=len(result))
            logger.info(f"[FieldValueMerge] Merge completed: {len(result)} records, {len(df.columns)} fields")
            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_value_merge.errors.merge_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[FieldValueMerge] Merge failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def _convert_value_type(self, series: pd.Series, value_type: str, decimal_precision: int) -> pd.Series:
        """转换值类型"""
        try:
            if value_type == "string":
                return series.astype(str)
            if value_type == "integer":
                # 先转 float 再转 int，避免 NaN 报错
                return series.fillna(0).astype(float).astype(int)
            if value_type == "float":
                return series.astype(float).round(decimal_precision)
            if value_type == "boolean":
                return series.astype(bool)
            logger.warning(f"[FieldValueMerge] Unknown value type: {value_type}, keeping as is")
            return series
        except Exception as e:
            logger.warning(f"[FieldValueMerge] Type conversion failed: {e}, keeping as is")
            return series

    def preview_fields(self) -> Data:
        """预览合并后的字段信息"""
        try:
            if not self.data_input:
                return Data(
                    data={
                        "fields": [],
                        "message": i18n.t("components.manipulations.field_value_merge.errors.no_input_data"),
                    }
                )

            # 获取原始字段
            original_fields = self._extract_field_names(self.data_input)

            # 计算新增字段
            new_fields = []
            removed_fields = set()

            if self.merge_configs:
                for config in self.merge_configs:
                    new_field = config.get("new_field")
                    operation = config.get("operation", "A LINK B")
                    field_a = config.get("field_a")
                    field_b = config.get("field_b")
                    value_type = config.get("value_type", "string")

                    if new_field and field_a and field_b:
                        new_fields.append(
                            {
                                "field_name": new_field,
                                "operation": operation,
                                "source": f"{field_a} {operation} {field_b}",
                                "value_type": value_type,
                            }
                        )

                        if self.drop_source_fields:
                            removed_fields.add(field_a)
                            removed_fields.add(field_b)

            # 计算最终字段列表
            final_fields = [f for f in original_fields if f not in removed_fields]
            final_fields.extend([nf["field_name"] for nf in new_fields])

            return Data(
                data={
                    "original_fields": original_fields,
                    "original_count": len(original_fields),
                    "new_fields": new_fields,
                    "new_count": len(new_fields),
                    "removed_fields": list(removed_fields),
                    "removed_count": len(removed_fields),
                    "final_fields": final_fields,
                    "final_count": len(final_fields),
                }
            )

        except Exception as e:
            logger.error(f"[FieldValueMerge] Field preview failed: {e}")
            return Data(data={"error": str(e)})
