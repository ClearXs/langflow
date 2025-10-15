import os
from __future__ import annotations

import json
from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data


class FieldMapperComponent(Component):
    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    display_name = i18n.t('components.data.field_mapper.display_name')
    description = i18n.t('components.data.field_mapper.description')
    icon = "arrow-right-left"
    name = "FieldMapper"

    inputs = [
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.field_mapper.data.display_name'),
            info=i18n.t('components.data.field_mapper.data.info'),
            input_types=["Data"]
        ),
        MessageTextInput(
            name="field_mappings",
            display_name=i18n.t('components.data.field_mapper.field_mappings.display_name'),
            info=i18n.t('components.data.field_mapper.field_mappings.info'),
            is_list=True,
            tool_mode=True,
            field_type="FieldMappingTableInput",
        ),
    ]

    outputs = [
        Output(
            name="mapped_data",
            display_name=i18n.t('components.data.field_mapper.outputs.mapped_data.display_name'),
            method="map_fields"
        ),
    ]

    def map_fields(self) -> list[Data]:
        """Map fields from source to target based on field mappings."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.field_mapper.errors.no_data'))

            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.field_mapper.errors.empty_data'))

            mappings = self._parse_field_mappings()
            if not mappings:
                raise ValueError(i18n.t('components.data.field_mapper.errors.no_mappings'))

            mapped_data = []
            for record in data_list:
                if not isinstance(record, dict):
                    continue

                mapped_record = {}
                for mapping in mappings:
                    src_col = mapping.get('src_col')
                    tgt_col = mapping.get('tgt_col')
                    tgt_type = mapping.get('tgt_type', 'string')
                    tgt_unit = mapping.get('tgt_unit', '')
                    is_enabled = mapping.get('enabled', True)

                    if not is_enabled or not src_col or not tgt_col:
                        continue

                    if src_col in record:
                        value = record[src_col]
                        converted_value = self._convert_value(value, tgt_type)

                        if tgt_unit:
                            mapped_record[tgt_col] = {
                                'value': converted_value,
                                'unit': tgt_unit
                            }
                        else:
                            mapped_record[tgt_col] = converted_value

                mapped_data.append(Data(data=mapped_record))

            self.status = f"Mapped {len(mappings)} fields across {len(mapped_data)} records"
            return mapped_data

        except Exception as e:
            error_message = i18n.t('components.data.field_mapper.errors.mapping_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _parse_input_data(self) -> list[dict]:
        """Parse input data from various formats."""
        if isinstance(self.data, list):
            return [item.data if hasattr(item, 'data') else item for item in self.data]
        elif hasattr(self.data, 'data'):
            data_content = self.data.data
            return data_content if isinstance(data_content, list) else [data_content]
        elif isinstance(self.data, str):
            try:
                parsed = json.loads(self.data)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                raise ValueError(i18n.t('components.data.field_mapper.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _parse_field_mappings(self) -> list[dict]:
        """Parse field mappings from input."""
        if not self.field_mappings:
            return []

        if isinstance(self.field_mappings, str):
            try:
                mappings = json.loads(self.field_mappings)
                return mappings if isinstance(mappings, list) else []
            except json.JSONDecodeError:
                return []
        elif isinstance(self.field_mappings, list):
            return self.field_mappings
        else:
            return []

    def _convert_value(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if value is None:
            return None

        try:
            if target_type == 'string':
                return str(value)
            elif target_type == 'integer':
                return int(float(value))
            elif target_type == 'float':
                return float(value)
            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                return value
        except (ValueError, TypeError):
            return value
