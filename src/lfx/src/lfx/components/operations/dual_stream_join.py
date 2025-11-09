import asyncio
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, MessageTextInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLDualStreamJoinComponent(Component):
    display_name = i18n.t("components.operations.dual_stream_join.display_name")
    description = i18n.t("components.operations.dual_stream_join.description")
    icon = "git-merge"
    name = "ETLDualStreamJoin"

    inputs = [
        DataInput(
            name="left_stream",
            display_name=i18n.t("components.operations.dual_stream_join.left_stream.display_name"),
            info=i18n.t("components.operations.dual_stream_join.left_stream.info"),
            is_list=True,
            required=True,
        ),
        DataInput(
            name="right_stream",
            display_name=i18n.t("components.operations.dual_stream_join.right_stream.display_name"),
            info=i18n.t("components.operations.dual_stream_join.right_stream.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="join_type",
            display_name=i18n.t("components.operations.dual_stream_join.join_type.display_name"),
            info=i18n.t("components.operations.dual_stream_join.join_type.info"),
            options=["inner", "left", "right", "outer"],
            value="inner",
        ),
        TableInput(
            name="join_conditions",
            display_name=i18n.t("components.operations.dual_stream_join.join_conditions.display_name"),
            info=i18n.t("components.operations.dual_stream_join.join_conditions.info"),
            table_schema=[
                {
                    "name": "left_key",
                    "display_name": i18n.t("components.operations.dual_stream_join.join_conditions.left_key"),
                    "type": "str",
                    "options": [],  # 动态加载
                },
                {
                    "name": "operator",
                    "display_name": i18n.t("components.operations.dual_stream_join.join_conditions.operator"),
                    "type": "str",
                    "options": ["=", "!=", ">", "<", ">=", "<="],
                },
                {
                    "name": "right_key",
                    "display_name": i18n.t("components.operations.dual_stream_join.join_conditions.right_key"),
                    "type": "str",
                    "options": [],  # 动态加载
                },
            ],
            value=[],
            table_options={
                "block_add": False,  # 允许添加多个连接条件
                "block_delete": False,
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.operations.dual_stream_join.join_conditions.load_fields_button"),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
            required=True,
        ),
        TableInput(
            name="output_fields",
            display_name=i18n.t("components.operations.dual_stream_join.output_fields.display_name"),
            info=i18n.t("components.operations.dual_stream_join.output_fields.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.operations.dual_stream_join.output_fields.field_name"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "source",
                    "display_name": i18n.t("components.operations.dual_stream_join.output_fields.source"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.operations.dual_stream_join.output_fields.data_type"),
                    "type": "str",
                    "disable_edit": True,
                },
            ],
            value=[],
            table_options={
                "block_add": True,  # 禁止手动添加
                "block_delete": True,  # 禁止手动删除
                "action_buttons": [
                    {
                        "name": "preview_output_fields",
                        "label": i18n.t("components.operations.dual_stream_join.output_fields.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        MessageTextInput(
            name="left_prefix",
            display_name=i18n.t("components.operations.dual_stream_join.left_prefix.display_name"),
            info=i18n.t("components.operations.dual_stream_join.left_prefix.info"),
            value="left_",
            advanced=True,
        ),
        MessageTextInput(
            name="right_prefix",
            display_name=i18n.t("components.operations.dual_stream_join.right_prefix.display_name"),
            info=i18n.t("components.operations.dual_stream_join.right_prefix.info"),
            value="right_",
            advanced=True,
        ),
        BoolInput(
            name="drop_duplicates",
            display_name=i18n.t("components.operations.dual_stream_join.drop_duplicates.display_name"),
            info=i18n.t("components.operations.dual_stream_join.drop_duplicates.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.operations.dual_stream_join.outputs.data"),
            method="join_streams",
        ),
        Output(
            name="join_stats",
            display_name=i18n.t("components.operations.dual_stream_join.outputs.join_stats"),
            method="get_join_stats",
        ),
        Output(
            name="field_preview",
            display_name=i18n.t("components.operations.dual_stream_join.outputs.field_preview"),
            method="preview_fields",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """动态更新join_conditions和output_fields的字段选项"""
        logger.info(f"[DualStreamJoin] update_build_config called - field_name: {field_name}, action: {action}")

        # 获取graph_data和node_id用于获取上游数据
        graph_data = build_config.get("_graph_data", {})
        node_id = build_config.get("_node_id")

        # 如果没有graph_data，尝试从self.graph获取
        if not graph_data and hasattr(self, "graph") and self.graph is not None:
            if hasattr(self.graph, "data"):
                graph_data = self.graph.data
            else:
                logger.warning("[DualStreamJoin] PlaceholderGraph detected - no graph data available")

        # 处理"加载字段列表"按钮点击
        if field_name == "join_conditions" and action == "load_fields":
            try:
                if not graph_data:
                    logger.warning("[DualStreamJoin] No graph data available")
                    self.status = i18n.t("components.operations.dual_stream_join.errors.no_graph_data")
                    return build_config

                left_fields = []
                right_fields = []

                # Primary strategy: Try to execute upstream nodes to get actual data
                # Enhanced with retry mechanism for "has not been built yet" errors
                max_retries = 2
                left_data = None
                right_data = None

                for attempt in range(max_retries):
                    try:
                        left_data = await self.get_upstream_data(
                            input_name="left_stream", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )
                        right_data = await self.get_upstream_data(
                            input_name="right_stream", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        # 提取字段列表
                        left_fields = self._extract_field_names(left_data) if left_data else []
                        right_fields = self._extract_field_names(right_data) if right_data else []

                        if left_fields or right_fields:
                            logger.info(
                                f"[DualStreamJoin] Extracted fields from upstream data - left: {len(left_fields)}, right: {len(right_fields)} (attempt {attempt + 1})"
                            )
                            break
                        logger.warning(f"[DualStreamJoin] No data returned from upstream nodes (attempt {attempt + 1})")

                    except ValueError as e:
                        error_msg = str(e)
                        if "has not been built yet" in error_msg and attempt < max_retries - 1:
                            logger.warning(f"[DualStreamJoin] Upstream node not built, retrying... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(0.2)  # Brief delay before retry
                            continue
                        # Fallback strategy: Extract from upstream node configurations
                        logger.warning(f"[DualStreamJoin] Upstream execution failed after {attempt + 1} attempts: {e}. Trying static analysis...")
                        break
                    except Exception as e:
                        logger.warning(f"[DualStreamJoin] Unexpected error during upstream execution: {e}. Falling back to static analysis...")
                        break

                # If we couldn't get data from execution, try static analysis
                if not left_data and not right_data:
                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        # Extract from both inputs
                        left_fields_dicts = find_and_extract_upstream_fields(
                            graph_data, node_id, "left_stream", "DualStreamJoin"
                        )

                        right_fields_dicts = find_and_extract_upstream_fields(
                            graph_data, node_id, "right_stream", "DualStreamJoin"
                        )

                        if left_fields_dicts or right_fields_dicts:
                            left_fields = [field["name"] for field in left_fields_dicts] if left_fields_dicts else []
                            right_fields = [field["name"] for field in right_fields_dicts] if right_fields_dicts else []
                            logger.info(
                                f"[DualStreamJoin] Extracted fields from static config - left: {len(left_fields)}, right: {len(right_fields)}"
                            )

                    except Exception:  # noqa: BLE001
                        logger.exception("[DualStreamJoin] Static analysis also failed")

                # Update build_config with results
                if left_fields and right_fields:
                    # 1. 更新 table_schema 的 options
                    build_config["join_conditions"]["table_schema"][0]["options"] = left_fields  # left_key
                    build_config["join_conditions"]["table_schema"][2]["options"] = right_fields  # right_key

                    # 2. 自动填充表格数据（如果当前为空）
                    if not build_config["join_conditions"].get("value"):
                        # 创建一个示例行，让用户知道如何配置
                        default_row = {
                            "left_key": left_fields[0],
                            "operator": "=",
                            "right_key": right_fields[0],
                        }
                        build_config["join_conditions"]["value"] = [default_row]

                    self.status = i18n.t(
                        "components.operations.dual_stream_join.status.fields_loaded",
                        left_count=len(left_fields),
                        right_count=len(right_fields),
                    )
                    logger.info(f"[DualStreamJoin] Loaded fields - left: {left_fields}, right: {right_fields}")
                else:
                    # 仍然更新选项，即使只有部分字段
                    if left_fields:
                        build_config["join_conditions"]["table_schema"][0]["options"] = left_fields
                    if right_fields:
                        build_config["join_conditions"]["table_schema"][2]["options"] = right_fields

                    self.status = i18n.t("components.operations.dual_stream_join.warnings.field_load_failed")
                    logger.warning("[DualStreamJoin] Could not extract all fields")

            except Exception as e:  # noqa: BLE001
                logger.exception("[DualStreamJoin] Failed to load fields")
                self.status = i18n.t("components.operations.dual_stream_join.errors.load_fields_failed", error=str(e))

        # 处理"预览输出字段"按钮点击
        elif field_name == "output_fields" and action == "preview_output_fields":
            try:
                if not graph_data:
                    logger.warning("[DualStreamJoin] No graph data available for preview")
                    self.status = i18n.t("components.operations.dual_stream_join.errors.no_graph_data")
                    return build_config

                output_fields = []
                left_data = None
                right_data = None

                # Primary strategy: Try to execute upstream nodes to get actual data
                try:
                    left_data = await self.get_upstream_data(
                        input_name="left_stream", graph_data=graph_data, sample_size=10, vertex_id=node_id
                    )
                    right_data = await self.get_upstream_data(
                        input_name="right_stream", graph_data=graph_data, sample_size=10, vertex_id=node_id
                    )

                    # 生成输出字段预览
                    output_fields = self._generate_output_fields_preview(left_data, right_data)

                    if output_fields:
                        logger.info(f"[DualStreamJoin] Generated {len(output_fields)} output fields from upstream data")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configurations
                    logger.warning(f"[DualStreamJoin] Upstream execution failed for preview: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        # Extract field names from both inputs
                        left_fields_dicts = find_and_extract_upstream_fields(
                            graph_data, node_id, "left_stream", "DualStreamJoin"
                        )
                        right_fields_dicts = find_and_extract_upstream_fields(
                            graph_data, node_id, "right_stream", "DualStreamJoin"
                        )

                        # Generate simple preview without data types
                        if left_fields_dicts or right_fields_dicts:
                            output_fields = []
                            for field_dict in (left_fields_dicts or []):
                                output_fields.append(
                                    {
                                        "field_name": field_dict["name"],
                                        "source": "left",
                                        "data_type": field_dict.get("type", "unknown"),
                                    }
                                )
                            for field_dict in (right_fields_dicts or []):
                                output_fields.append(
                                    {
                                        "field_name": field_dict["name"],
                                        "source": "right",
                                        "data_type": field_dict.get("type", "unknown"),
                                    }
                                )

                            logger.info(
                                f"[DualStreamJoin] Generated {len(output_fields)} output fields from static config"
                            )

                    except Exception:  # noqa: BLE001
                        logger.exception("[DualStreamJoin] Static analysis for preview also failed")

                # Update build_config with results
                if output_fields:
                    build_config["output_fields"]["value"] = output_fields
                    self.status = i18n.t(
                        "components.operations.dual_stream_join.status.preview_success", count=len(output_fields)
                    )
                    logger.info(f"[DualStreamJoin] Generated {len(output_fields)} output field previews")
                else:
                    self.status = i18n.t("components.operations.dual_stream_join.warnings.field_load_failed")
                    logger.warning("[DualStreamJoin] Could not generate output field preview")

            except Exception as e:  # noqa: BLE001
                logger.exception("[DualStreamJoin] Failed to preview fields")
                self.status = i18n.t("components.operations.dual_stream_join.errors.preview_failed", error=str(e))

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

    def _generate_output_fields_preview(
        self, left_data: list[Data] | None, right_data: list[Data] | None
    ) -> list[dict]:
        """生成输出字段预览列表

        Args:
            left_data: 左流数据
            right_data: 右流数据

        Returns:
            字段预览列表，包含field_name、source、data_type
        """
        try:
            if not left_data and not right_data:
                return []

            left_fields = self._extract_field_names(left_data) if left_data else []
            right_fields = self._extract_field_names(right_data) if right_data else []

            # 获取样本数据用于类型推断
            left_sample = left_data[0].data if left_data and hasattr(left_data[0], "data") else {}
            right_sample = right_data[0].data if right_data and hasattr(right_data[0], "data") else {}

            output_fields = []

            # 公共字段（会有冲突，需要前缀）
            common_fields = set(left_fields) & set(right_fields)
            for field in common_fields:
                # 左表版本
                output_fields.append(
                    {
                        "field_name": f"{field}_{self.left_prefix}" if self.left_prefix else f"{field}_left",
                        "source": i18n.t("components.operations.dual_stream_join.output_fields.left_table"),
                        "data_type": self._infer_data_type(left_sample.get(field)),
                    }
                )
                # 右表版本
                output_fields.append(
                    {
                        "field_name": f"{field}_{self.right_prefix}" if self.right_prefix else f"{field}_right",
                        "source": i18n.t("components.operations.dual_stream_join.output_fields.right_table"),
                        "data_type": self._infer_data_type(right_sample.get(field)),
                    }
                )

            # 左表独有字段
            left_only = set(left_fields) - common_fields
            for field in left_only:
                output_fields.append(
                    {
                        "field_name": field,
                        "source": i18n.t("components.operations.dual_stream_join.output_fields.left_table"),
                        "data_type": self._infer_data_type(left_sample.get(field)),
                    }
                )

            # 右表独有字段
            right_only = set(right_fields) - common_fields
            for field in right_only:
                output_fields.append(
                    {
                        "field_name": field,
                        "source": i18n.t("components.operations.dual_stream_join.output_fields.right_table"),
                        "data_type": self._infer_data_type(right_sample.get(field)),
                    }
                )

            return output_fields

        except Exception:  # noqa: BLE001
            logger.exception("[DualStreamJoin] Failed to generate output fields preview")
            return []

    def _infer_data_type(self, value: Any) -> str:
        """推断数据类型

        Args:
            value: 字段值

        Returns:
            类型字符串：integer、float、boolean、datetime、string
        """
        if value is None:
            return "string"

        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
            return "datetime"
        return "string"

    def join_streams(self) -> list[Data]:
        """使用多条件、多操作符进行Join合并"""
        try:
            self.status = i18n.t("components.operations.dual_stream_join.status.joining")
            logger.info(f"[DualStreamJoin] Starting join: {self.join_type}")

            # 验证输入
            if not self.left_stream or not self.right_stream:
                raise ValueError(i18n.t("components.operations.dual_stream_join.errors.missing_streams"))

            if not self.join_conditions:
                raise ValueError(i18n.t("components.operations.dual_stream_join.errors.missing_conditions"))

            logger.debug(f"[DualStreamJoin] Left stream: {len(self.left_stream)} records")
            logger.debug(f"[DualStreamJoin] Right stream: {len(self.right_stream)} records")
            logger.debug(f"[DualStreamJoin] Conditions: {self.join_conditions}")

            # 转换为DataFrame
            left_df = self._convert_to_dataframe(self.left_stream)
            right_df = self._convert_to_dataframe(self.right_stream)

            # 验证字段存在
            self._validate_join_fields(left_df, right_df)

            # 处理连接条件
            # 分离等值条件和非等值条件
            eq_conditions = [c for c in self.join_conditions if c.get("operator") == "="]
            neq_conditions = [c for c in self.join_conditions if c.get("operator") != "="]

            # 先执行等值连接
            if eq_conditions:
                left_keys = [c["left_key"] for c in eq_conditions]
                right_keys = [c["right_key"] for c in eq_conditions]

                # 对齐连接键的数据类型
                left_df, right_df = self._align_join_key_types(left_df, right_df, left_keys, right_keys)

                joined_df = pd.merge(
                    left_df,
                    right_df,
                    left_on=left_keys,
                    right_on=right_keys,
                    how=self.join_type,
                    suffixes=(f"_{self.left_prefix}", f"_{self.right_prefix}"),
                )
            else:
                # 没有等值条件，使用笛卡尔积
                left_df["_join_key"] = 1
                right_df["_join_key"] = 1
                joined_df = pd.merge(
                    left_df,
                    right_df,
                    on="_join_key",
                    how=self.join_type,
                    suffixes=(f"_{self.left_prefix}", f"_{self.right_prefix}"),
                )
                joined_df.drop("_join_key", axis=1, inplace=True)

            # 应用非等值条件过滤
            if neq_conditions:
                for cond in neq_conditions:
                    left_key = cond["left_key"]
                    operator = cond["operator"]
                    right_key = cond["right_key"]

                    # 构建过滤条件
                    if operator == "!=":
                        joined_df = joined_df[joined_df[left_key] != joined_df[right_key]]
                    elif operator == ">":
                        joined_df = joined_df[joined_df[left_key] > joined_df[right_key]]
                    elif operator == "<":
                        joined_df = joined_df[joined_df[left_key] < joined_df[right_key]]
                    elif operator == ">=":
                        joined_df = joined_df[joined_df[left_key] >= joined_df[right_key]]
                    elif operator == "<=":
                        joined_df = joined_df[joined_df[left_key] <= joined_df[right_key]]

            # 去重
            if self.drop_duplicates:
                joined_df = joined_df.drop_duplicates()

            # 转换为Data对象
            result_data = []
            for _, row in joined_df.iterrows():
                row_dict = row.to_dict()
                row_dict["_join_type"] = self.join_type
                result_data.append(Data(data=row_dict))

            logger.info(f"[DualStreamJoin] Join completed: {len(result_data)} records")
            self.status = i18n.t("components.operations.dual_stream_join.status.success", records=len(result_data))
            return result_data

        except KeyError as e:
            error_msg = i18n.t("components.operations.dual_stream_join.errors.field_not_found", field=str(e))
            self.status = error_msg
            logger.error(f"[DualStreamJoin] Field not found: {e}")
            raise ValueError(error_msg) from e
        except pd.errors.MergeError as e:
            error_msg = i18n.t("components.operations.dual_stream_join.errors.merge_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[DualStreamJoin] Merge error: {e}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t("components.operations.dual_stream_join.errors.join_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[DualStreamJoin] Unexpected error: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def _validate_join_fields(self, left_df: pd.DataFrame, right_df: pd.DataFrame) -> None:
        """验证连接字段是否存在于数据流中"""
        left_fields = set(left_df.columns)
        right_fields = set(right_df.columns)

        for cond in self.join_conditions:
            left_key = cond.get("left_key")
            right_key = cond.get("right_key")

            if left_key not in left_fields:
                raise ValueError(
                    i18n.t("components.operations.dual_stream_join.errors.left_field_not_found", field=left_key)
                )

            if right_key not in right_fields:
                raise ValueError(
                    i18n.t("components.operations.dual_stream_join.errors.right_field_not_found", field=right_key)
                )

    def _align_join_key_types(
        self, left_df: pd.DataFrame, right_df: pd.DataFrame, left_keys: list[str], right_keys: list[str]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """对齐左右表连接键的数据类型，确保类型兼容"""
        left_df = left_df.copy()
        right_df = right_df.copy()

        for left_key, right_key in zip(left_keys, right_keys, strict=False):
            left_dtype = left_df[left_key].dtype
            right_dtype = right_df[right_key].dtype

            # 如果类型已经相同，跳过
            if left_dtype == right_dtype:
                continue

            logger.debug(
                f"[DualStreamJoin] Type mismatch detected - {left_key}:{left_dtype} vs {right_key}:{right_dtype}"
            )

            # 优先尝试转换为数值类型
            left_numeric = pd.to_numeric(left_df[left_key], errors="coerce")
            right_numeric = pd.to_numeric(right_df[right_key], errors="coerce")

            # 如果两者都能成功转换为数值（没有全部变成NaN），则使用数值类型
            if not left_numeric.isna().all() and not right_numeric.isna().all():
                # 检查是否可以转换为整数（没有小数部分）
                if (left_numeric.dropna() % 1 == 0).all() and (right_numeric.dropna() % 1 == 0).all():
                    # 转换为int64（处理NaN）
                    left_df[left_key] = left_numeric.fillna(-999999).astype("int64")
                    right_df[right_key] = right_numeric.fillna(-999999).astype("int64")
                    logger.info(f"[DualStreamJoin] Converted {left_key} and {right_key} to int64")
                else:
                    # 转换为float64
                    left_df[left_key] = left_numeric
                    right_df[right_key] = right_numeric
                    logger.info(f"[DualStreamJoin] Converted {left_key} and {right_key} to float64")
            else:
                # 无法转换为数值，统一转换为字符串
                left_df[left_key] = left_df[left_key].astype(str)
                right_df[right_key] = right_df[right_key].astype(str)
                logger.info(f"[DualStreamJoin] Converted {left_key} and {right_key} to string")

        return left_df, right_df

    def _convert_to_dataframe(self, data_list: list[Data]) -> pd.DataFrame:
        """Convert list of Data objects to pandas DataFrame."""
        records = []
        for data_obj in data_list:
            if hasattr(data_obj, "data") and isinstance(data_obj.data, dict):
                records.append(data_obj.data)
            elif isinstance(data_obj, dict):
                records.append(data_obj)

        return pd.DataFrame(records)

    def get_join_stats(self) -> Data:
        """Get statistics about the join operation."""
        joined = self.join_streams()

        stats = {
            "join_type": self.join_type,
            "left_stream_count": len(self.left_stream) if self.left_stream else 0,
            "right_stream_count": len(self.right_stream) if self.right_stream else 0,
            "joined_count": len(joined),
            "join_keys": [
                cond["left_key"] + " " + cond.get("operator", "=") + " " + cond["right_key"]
                for cond in self.join_conditions
            ],
        }

        return Data(data=stats)

    def preview_fields(self) -> Data:
        """预览合并后的字段信息"""
        try:
            if not self.left_stream or not self.right_stream:
                return Data(
                    data={
                        "fields": [],
                        "message": i18n.t("components.operations.dual_stream_join.errors.no_streams_for_preview"),
                    }
                )

            left_fields = self._extract_field_names(self.left_stream)
            right_fields = self._extract_field_names(self.right_stream)

            # 分析字段来源
            field_info = []

            # 公共字段
            common_fields = set(left_fields) & set(right_fields)
            for field in common_fields:
                field_info.append(
                    {
                        "field_name": field,
                        "source": i18n.t("components.operations.dual_stream_join.field_preview.common_field"),
                        "conflict_resolution": i18n.t(
                            "components.operations.dual_stream_join.field_preview.use_prefix",
                            left_prefix=self.left_prefix,
                            field=field,
                            right_prefix=self.right_prefix,
                        ),
                    }
                )

            # 左表独有
            left_only = set(left_fields) - common_fields
            for field in left_only:
                field_info.append(
                    {
                        "field_name": field,
                        "source": i18n.t("components.operations.dual_stream_join.field_preview.left_table"),
                        "conflict_resolution": i18n.t(
                            "components.operations.dual_stream_join.field_preview.no_conflict"
                        ),
                    }
                )

            # 右表独有
            right_only = set(right_fields) - common_fields
            for field in right_only:
                field_info.append(
                    {
                        "field_name": field,
                        "source": i18n.t("components.operations.dual_stream_join.field_preview.right_table"),
                        "conflict_resolution": i18n.t(
                            "components.operations.dual_stream_join.field_preview.no_conflict"
                        ),
                    }
                )

            return Data(
                data={
                    "total_fields": len(field_info),
                    "left_fields_count": len(left_fields),
                    "right_fields_count": len(right_fields),
                    "common_fields_count": len(common_fields),
                    "fields": field_info,
                }
            )

        except Exception as e:
            logger.error(f"[DualStreamJoin] Field preview failed: {e}")
            return Data(data={"error": str(e)})
