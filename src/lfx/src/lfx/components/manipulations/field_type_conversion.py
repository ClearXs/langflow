import asyncio
from datetime import datetime
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFieldTypeConversion(Component):
    display_name = i18n.t("components.manipulations.field_type_conversion.display_name")
    description = i18n.t("components.manipulations.field_type_conversion.description")
    icon = "FileType"
    name = "ETLFieldTypeConversion"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_type_conversion.data_input.display_name"),
            info=i18n.t("components.manipulations.field_type_conversion.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="type_conversions",
            display_name=i18n.t("components.manipulations.field_type_conversion.type_conversions.display_name"),
            info=i18n.t("components.manipulations.field_type_conversion.type_conversions.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.field_name.display_name"
                    ),
                    "info": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.field_name.info"
                    ),
                    "type": "str",
                    "required": True,
                },
                {
                    "name": "source_type",
                    "display_name": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.source_type.display_name"
                    ),
                    "info": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.source_type.info"
                    ),
                    "type": "str",
                    "disable_edit": True,
                    "formatter": "code",
                    "translate_value": False,
                },
                {
                    "name": "target_type",
                    "display_name": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.target_type.display_name"
                    ),
                    "info": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.target_type.info"
                    ),
                    "type": "str",
                    "formatter": "text",
                    "options": ["string", "integer", "float", "boolean", "datetime"],
                    "required": True,
                },
                {
                    "name": "conversion_rule",
                    "display_name": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.conversion_rule.display_name"
                    ),
                    "info": i18n.t(
                        "components.manipulations.field_type_conversion.type_conversions.conversion_rule.info"
                    ),
                    "type": "str",
                    "options_map": {
                        "datetime": [
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.default"), "value": ""},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.yyyy_mm_dd"), "value": "yyyy-MM-dd"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.yyyy_mm_dd_hh_mm_ss"), "value": "yyyy-MM-dd HH:mm:ss"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.yyyy_mm_dd_slash"), "value": "yyyy/MM/dd"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.dd_mm_yyyy"), "value": "dd/MM/yyyy"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.mm_dd_yyyy"), "value": "MM/dd/yyyy"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.datetime.iso8601"), "value": "ISO8601"},
                        ],
                        "boolean": [
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.boolean.default"), "value": ""},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.boolean.true_values"), "value": "true,1,yes"},
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.boolean.false_values"), "value": "false,0,no"},
                        ],
                        "string": [
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.default"), "value": ""}
                        ],
                        "integer": [
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.default"), "value": ""}
                        ],
                        "float": [
                            {"label": i18n.t("components.manipulations.field_type_conversion.rules.default"), "value": ""}
                        ],
                    },
                    "depend_on": "target_type",
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.manipulations.field_type_conversion.actions.load_fields"),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="strict_validation",
            display_name=i18n.t("components.manipulations.field_type_conversion.strict_validation.display_name"),
            info=i18n.t("components.manipulations.field_type_conversion.strict_validation.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_type_conversion.outputs.data.display_name"),
            method="convert_types",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,  # noqa: ARG002
        field_name: str | None = None,
        action: str | None = None,
    ) -> dict:
        """处理加载字段动作按钮."""
        if field_name == "type_conversions" and action == "load_fields":
            try:
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # 策略1: 尝试运行时执行获取实际数据
                upstream_data = None
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input",
                            graph_data=graph_data,
                            sample_size=100,
                            vertex_id=node_id,
                        )
                        if upstream_data:
                            break
                    except ValueError as e:
                        if "has not been built yet" in str(e) and attempt < max_retries - 1:
                            await asyncio.sleep(0.2)
                            continue
                        logger.warning(f"Runtime execution failed: {e}")
                        break
                    except Exception as e:
                        logger.warning(f"Runtime execution failed: {e}")
                        break

                # 获取字段信息
                if upstream_data:
                    field_info = self._analyze_field_types(upstream_data)
                else:
                    # 策略2: 静态分析上游节点配置
                    from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                    field_info = find_and_extract_upstream_fields(
                        graph_data, node_id, "data_input", "ETLFieldTypeConversion"
                    )
                    # 静态分析无法获取类型，默认为 string
                    field_info = dict.fromkeys(field_info, "string")

                # 生成类型转换配置行
                conversions = []
                for field_name_item, detected_type in field_info.items():
                    conversions.append({
                        "field_name": field_name_item,
                        "source_type": detected_type,
                        "target_type": detected_type,
                        "conversion_rule": "",
                    })

                build_config["type_conversions"]["value"] = conversions
                self.status = i18n.t(
                    "components.manipulations.field_type_conversion.status.detected", count=len(conversions)
                )

            except Exception as e:
                logger.exception(f"[ETLFieldTypeConversion] Type detection failed: {e}")
                self.status = i18n.t(
                    "components.manipulations.field_type_conversion.errors.detection_failed", error=str(e)
                )

        return build_config

    def _analyze_field_types(self, data_items: list[Data]) -> dict[str, str]:
        """分析数据样本, 推断字段类型."""
        field_types = {}

        for data_item in data_items:
            if not hasattr(data_item, "data") or not isinstance(data_item.data, dict):
                continue

            for field_name, value in data_item.data.items():
                if value is None:
                    continue

                detected_type = self._infer_type(value)

                # 使用最宽松的类型（如果同一字段有多个类型）
                if field_name not in field_types:
                    field_types[field_name] = detected_type
                else:
                    field_types[field_name] = self._merge_types(field_types[field_name], detected_type)

        return field_types

    def _infer_type(self, value: Any) -> str:
        """推断单个值的类型."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, datetime):
            return "datetime"
        if isinstance(value, str):
            # 尝试识别字符串中的特殊类型
            if value.lower() in ("true", "false", "yes", "no", "1", "0"):
                return "boolean"
            try:
                int(value)
                return "integer"
            except ValueError:
                pass
            try:
                float(value)
                return "float"
            except ValueError:
                pass
            try:
                pd.to_datetime(value)
                return "datetime"
            except Exception:
                pass
        return "string"

    def _merge_types(self, type1: str, type2: str) -> str:
        """合并两个类型, 选择更宽松的类型."""
        type_hierarchy = ["boolean", "integer", "float", "datetime", "string"]
        idx1 = type_hierarchy.index(type1) if type1 in type_hierarchy else -1
        idx2 = type_hierarchy.index(type2) if type2 in type_hierarchy else -1
        return type_hierarchy[max(idx1, idx2)]

    def _check_data_loss_warning(self, source_type: str, target_type: str) -> str:
        """检查类型转换是否可能丢失数据."""
        warnings = []

        # Float -> Integer: 丢失小数部分
        if source_type == "float" and target_type == "integer":
            warnings.append(i18n.t("components.manipulations.field_type_conversion.warnings.decimal_loss"))

        # String -> Number: 可能解析失败
        if source_type == "string" and target_type in ("integer", "float"):
            warnings.append(i18n.t("components.manipulations.field_type_conversion.warnings.parse_failure"))

        # Datetime -> String: 丢失时区信息
        if source_type == "datetime" and target_type == "string":
            warnings.append(i18n.t("components.manipulations.field_type_conversion.warnings.timezone_loss"))

        # Any -> Boolean: 信息丢失
        if target_type == "boolean" and source_type not in ("boolean", "string"):
            warnings.append(i18n.t("components.manipulations.field_type_conversion.warnings.information_loss"))

        return "; ".join(warnings) if warnings else ""

    def convert_types(self) -> list[Data]:
        """执行类型转换并返回结果."""
        try:
            # 验证输入
            if not self.data_input:
                msg = i18n.t("components.manipulations.field_type_conversion.errors.no_input")
                raise ValueError(msg)

            type_conversions = getattr(self, "type_conversions", [])
            pass_through = getattr(self, "pass_through_unmapped", True)
            strict = getattr(self, "strict_validation", True)

            # 构建转换映射
            conversion_map = {}
            for conv in type_conversions:
                field_name = conv.get("field_name")
                if not field_name:
                    continue
                conversion_map[field_name] = {
                    "target_type": conv.get("target_type", "string"),
                    "conversion_rule": conv.get("conversion_rule", ""),
                }

            # 处理每条数据
            result = []
            for idx, data_item in enumerate(self.data_input):
                if not hasattr(data_item, "data") or not isinstance(data_item.data, dict):
                    continue

                converted_row = self._convert_row(
                    row=data_item.data,
                    conversion_map=conversion_map,
                    pass_through=pass_through,
                    strict=strict,
                    row_index=idx,
                )
                result.append(Data(data=converted_row))

            self.status = i18n.t("components.manipulations.field_type_conversion.status.success", count=len(result))
            return result

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t(
                "components.manipulations.field_type_conversion.errors.conversion_failed", error=str(e)
            )
            self.status = error_msg
            logger.exception(f"[ETLFieldTypeConversion] {error_msg}")
            raise ValueError(error_msg) from e

    def _convert_row(
        self,
        row: dict,
        conversion_map: dict,
        pass_through: bool,  # noqa: FBT001
        strict: bool,  # noqa: FBT001
        row_index: int,
    ) -> dict:
        """转换单行数据."""
        converted = {}

        for field_name, value in row.items():
            # 检查是否需要转换
            if field_name in conversion_map:
                conv_config = conversion_map[field_name]
                target_type = conv_config["target_type"]
                conversion_rule = conv_config["conversion_rule"]

                try:
                    converted_value = self._convert_value(
                        value=value,
                        target_type=target_type,
                        conversion_rule=conversion_rule,
                    )
                    converted[field_name] = converted_value
                except Exception as e:
                    if strict:
                        msg = i18n.t(
                            "components.manipulations.field_type_conversion.errors.field_conversion_failed",
                            row=row_index + 1,
                            field=field_name,
                            error=str(e),
                        )
                        raise ValueError(msg) from e
                    # 非严格模式：保留原值
                    logger.warning(
                        f"Row {row_index + 1}, field '{field_name}': {e}, keeping original value"
                    )
                    converted[field_name] = value
            elif pass_through:
                # 透传未配置的字段
                converted[field_name] = value
            # else: 不透传，忽略该字段

        return converted

    def _convert_value(self, value: Any, target_type: str, conversion_rule: str = "") -> Any:
        """转换单个值到目标类型."""
        # Null 处理
        if value is None or value == "":
            return None

        # String 转换
        if target_type == "string":
            return str(value)

        # Integer 转换
        if target_type == "integer":
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                return int(float(value))  # 支持 "3.14" -> 3
            return int(value)

        # Float 转换
        if target_type == "float":
            if isinstance(value, bool):
                return float(value)
            return float(value)

        # Boolean 转换
        if target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value_lower = value.lower().strip()
                # 支持自定义规则
                if conversion_rule:
                    true_values = [v.strip().lower() for v in conversion_rule.split(",")]
                    return value_lower in true_values
                # 默认规则
                if value_lower in ("true", "1", "yes", "y", "on"):
                    return True
                if value_lower in ("false", "0", "no", "n", "off"):
                    return False
                msg = f"Cannot convert '{value}' to boolean"
                raise ValueError(msg)
            return bool(value)

        # DateTime 转换
        if target_type == "datetime":
            if isinstance(value, datetime):
                # 如果有格式规则，格式化输出
                if conversion_rule:
                    return value.strftime(self._parse_datetime_format(conversion_rule))
                return value.isoformat()

            # 解析字符串为 datetime
            try:
                if conversion_rule:
                    # 使用指定格式解析
                    dt = datetime.strptime(str(value), self._parse_datetime_format(conversion_rule))
                else:
                    # 使用 pandas 自动解析
                    dt = pd.to_datetime(value)

                # 输出格式
                if conversion_rule:
                    return dt.strftime(self._parse_datetime_format(conversion_rule))
                return dt.isoformat()
            except Exception as e:
                msg = f"Cannot parse datetime: {e}"
                raise ValueError(msg) from e

        return value

    def _parse_datetime_format(self, format_str: str) -> str:
        """将用户友好的格式转换为 Python strftime 格式."""
        # 支持常见格式别名
        format_map = {
            "yyyy-MM-dd": "%Y-%m-%d",
            "yyyy-MM-dd HH:mm:ss": "%Y-%m-%d %H:%M:%S",
            "yyyy/MM/dd": "%Y/%m/%d",
            "dd/MM/yyyy": "%d/%m/%Y",
            "MM/dd/yyyy": "%m/%d/%Y",
            "ISO8601": "%Y-%m-%dT%H:%M:%S",
        }

        return format_map.get(format_str, format_str)
