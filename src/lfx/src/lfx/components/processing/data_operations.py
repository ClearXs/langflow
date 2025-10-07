import ast
import json
from typing import TYPE_CHECKING, Any
import i18n

import jq
from json_repair import repair_json

from lfx.custom import Component
from lfx.inputs import DictInput, DropdownInput, MessageTextInput, SortableListInput
from lfx.io import DataInput, MultilineInput, Output
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.schema.dotdict import dotdict
from lfx.utils.component_utils import set_current_fields, set_field_display

if TYPE_CHECKING:
    from collections.abc import Callable

ACTION_CONFIG = {
    "Select Keys": {"is_list": False, "log_msg": "setting filter fields"},
    "Literal Eval": {"is_list": False, "log_msg": "setting evaluate fields"},
    "Combine": {"is_list": True, "log_msg": "setting combine fields"},
    "Filter Values": {"is_list": False, "log_msg": "setting filter values fields"},
    "Append or Update": {"is_list": False, "log_msg": "setting Append or Update fields"},
    "Remove Keys": {"is_list": False, "log_msg": "setting remove keys fields"},
    "Rename Keys": {"is_list": False, "log_msg": "setting rename keys fields"},
    "Path Selection": {"is_list": False, "log_msg": "setting mapped key extractor fields"},
    "JQ Expression": {"is_list": False, "log_msg": "setting parse json fields"},
}
OPERATORS = {
    "equals": lambda a, b: str(a) == str(b),
    "not equals": lambda a, b: str(a) != str(b),
    "contains": lambda a, b: str(b) in str(a),
    "starts with": lambda a, b: str(a).startswith(str(b)),
    "ends with": lambda a, b: str(a).endswith(str(b)),
}


class DataOperationsComponent(Component):
    display_name = i18n.t('components.processing.data_operations.display_name')
    description = i18n.t('components.processing.data_operations.description')
    icon = "file-json"
    name = "DataOperations"
    default_keys = ["operations", "data"]
    metadata = {
        "keywords": [
            "data",
            "operations",
            "filter values",
            "Append or Update",
            "remove keys",
            "rename keys",
            "select keys",
            "literal eval",
            "combine",
            "filter",
            "append",
            "update",
            "remove",
            "rename",
            "data operations",
            "data manipulation",
            "data transformation",
            "data filtering",
            "data selection",
            "data combination",
            "Parse JSON",
            "JSON Query",
            "JQ Query",
        ],
    }
    actions_data = {
        "Select Keys": ["select_keys_input", "operations"],
        "Literal Eval": [],
        "Combine": [],
        "Filter Values": ["filter_values", "operations", "operator", "filter_key"],
        "Append or Update": ["append_update_data", "operations"],
        "Remove Keys": ["remove_keys_input", "operations"],
        "Rename Keys": ["rename_keys_input", "operations"],
        "Path Selection": ["mapped_json_display", "selected_key", "operations"],
        "JQ Expression": ["query", "operations"],
    }

    @staticmethod
    def extract_all_paths(obj, path=""):
        paths = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else f".{k}"
                paths.append(new_path)
                paths.extend(
                    DataOperationsComponent.extract_all_paths(v, new_path))
        elif isinstance(obj, list) and obj:
            new_path = f"{path}[0]"
            paths.append(new_path)
            paths.extend(
                DataOperationsComponent.extract_all_paths(obj[0], new_path))
        return paths

    @staticmethod
    def remove_keys_recursive(obj, keys_to_remove):
        if isinstance(obj, dict):
            return {
                k: DataOperationsComponent.remove_keys_recursive(
                    v, keys_to_remove)
                for k, v in obj.items()
                if k not in keys_to_remove
            }
        if isinstance(obj, list):
            return [DataOperationsComponent.remove_keys_recursive(item, keys_to_remove) for item in obj]
        return obj

    @staticmethod
    def rename_keys_recursive(obj, rename_map):
        if isinstance(obj, dict):
            return {
                rename_map.get(k, k): DataOperationsComponent.rename_keys_recursive(v, rename_map)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [DataOperationsComponent.rename_keys_recursive(item, rename_map) for item in obj]
        return obj

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t(
                'components.processing.data_operations.data.display_name'),
            info=i18n.t('components.processing.data_operations.data.info'),
            required=True,
            is_list=True
        ),
        SortableListInput(
            name="operations",
            display_name=i18n.t(
                'components.processing.data_operations.operations.display_name'),
            placeholder=i18n.t(
                'components.processing.data_operations.operations.placeholder'),
            info=i18n.t(
                'components.processing.data_operations.operations.info'),
            options=[
                {"name": i18n.t(
                    'components.processing.data_operations.operations.select_keys'), "icon": "lasso-select"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.literal_eval'), "icon": "braces"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.combine'), "icon": "merge"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.filter_values'), "icon": "filter"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.append_update'), "icon": "circle-plus"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.remove_keys'), "icon": "eraser"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.rename_keys'), "icon": "pencil-line"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.path_selection'), "icon": "mouse-pointer"},
                {"name": i18n.t(
                    'components.processing.data_operations.operations.jq_expression'), "icon": "terminal"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # select keys inputs
        MessageTextInput(
            name="select_keys_input",
            display_name=i18n.t(
                'components.processing.data_operations.select_keys_input.display_name'),
            info=i18n.t(
                'components.processing.data_operations.select_keys_input.info'),
            show=False,
            is_list=True,
        ),
        # filter values inputs
        MessageTextInput(
            name="filter_key",
            display_name=i18n.t(
                'components.processing.data_operations.filter_key.display_name'),
            info=i18n.t(
                'components.processing.data_operations.filter_key.info'),
            is_list=True,
            show=False,
        ),
        DropdownInput(
            name="operator",
            display_name=i18n.t(
                'components.processing.data_operations.operator.display_name'),
            options=[
                i18n.t('components.processing.data_operations.operator.equals'),
                i18n.t('components.processing.data_operations.operator.not_equals'),
                i18n.t('components.processing.data_operations.operator.contains'),
                i18n.t('components.processing.data_operations.operator.starts_with'),
                i18n.t('components.processing.data_operations.operator.ends_with')
            ],
            info=i18n.t('components.processing.data_operations.operator.info'),
            value=i18n.t(
                'components.processing.data_operations.operator.equals'),
            advanced=False,
            show=False,
        ),
        DictInput(
            name="filter_values",
            display_name=i18n.t(
                'components.processing.data_operations.filter_values.display_name'),
            info=i18n.t(
                'components.processing.data_operations.filter_values.info'),
            show=False,
            is_list=True,
        ),
        # update/ Append data inputs
        DictInput(
            name="append_update_data",
            display_name=i18n.t(
                'components.processing.data_operations.append_update_data.display_name'),
            info=i18n.t(
                'components.processing.data_operations.append_update_data.info'),
            show=False,
            value={"key": "value"},
            is_list=True,
        ),
        # remove keys inputs
        MessageTextInput(
            name="remove_keys_input",
            display_name=i18n.t(
                'components.processing.data_operations.remove_keys_input.display_name'),
            info=i18n.t(
                'components.processing.data_operations.remove_keys_input.info'),
            show=False,
            is_list=True,
        ),
        # rename keys inputs
        DictInput(
            name="rename_keys_input",
            display_name=i18n.t(
                'components.processing.data_operations.rename_keys_input.display_name'),
            info=i18n.t(
                'components.processing.data_operations.rename_keys_input.info'),
            show=False,
            is_list=True,
            value={"old_key": "new_key"},
        ),
        MultilineInput(
            name="mapped_json_display",
            display_name=i18n.t(
                'components.processing.data_operations.mapped_json_display.display_name'),
            info=i18n.t(
                'components.processing.data_operations.mapped_json_display.info'),
            required=False,
            refresh_button=True,
            real_time_refresh=True,
            placeholder=i18n.t(
                'components.processing.data_operations.mapped_json_display.placeholder'),
            show=False,
        ),
        DropdownInput(
            name="selected_key",
            display_name=i18n.t(
                'components.processing.data_operations.selected_key.display_name'),
            options=[],
            required=False,
            dynamic=True,
            show=False
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.processing.data_operations.query.display_name'),
            info=i18n.t('components.processing.data_operations.query.info'),
            placeholder=i18n.t(
                'components.processing.data_operations.query.placeholder'),
            show=False,
        ),
    ]
    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.data_operations.outputs.data.display_name'),
            name="data_output",
            method="as_data"
        ),
    ]

    # Helper methods for data operations
    def get_data_dict(self) -> dict:
        """Extract data dictionary from Data object."""
        data = self.data[0] if isinstance(
            self.data, list) and len(self.data) == 1 else self.data
        return data.model_dump()

    def json_query(self) -> Data:
        """Execute JQ expression on data."""
        try:
            if not self.query or not self.query.strip():
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.empty_jq_query')
                self.status = error_msg
                raise ValueError(error_msg)

            raw_data = self.get_data_dict()
            input_str = json.dumps(raw_data)
            repaired = repair_json(input_str)
            data_json = json.loads(repaired)
            jq_input = data_json["data"] if isinstance(
                data_json, dict) and "data" in data_json else data_json
            results = jq.compile(self.query).input(jq_input).all()

            if not results:
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.no_jq_results')
                self.status = error_msg
                raise ValueError(error_msg)

            result = results[0] if len(results) == 1 else results

            if result is None or result == "None":
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.jq_null_result')
                self.status = error_msg
                raise ValueError(error_msg)

            if isinstance(result, dict):
                success_msg = i18n.t(
                    'components.processing.data_operations.success.jq_query_executed')
                self.status = success_msg
                return Data(data=result)

            success_msg = i18n.t(
                'components.processing.data_operations.success.jq_query_executed')
            self.status = success_msg
            return Data(data={"result": result})

        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.jq_query_failed', error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def get_normalized_data(self) -> dict:
        """Get normalized data dictionary, handling the 'data' key if present."""
        data_dict = self.get_data_dict()
        return data_dict.get("data", data_dict)

    def data_is_list(self) -> bool:
        """Check if data contains multiple items."""
        return isinstance(self.data, list) and len(self.data) > 1

    def validate_single_data(self, operation: str) -> None:
        """Validate that the operation is being performed on a single data object."""
        if self.data_is_list():
            error_msg = i18n.t('components.processing.data_operations.errors.multiple_data_not_supported',
                               operation=operation)
            raise ValueError(error_msg)

    def operation_exception(self, operations: list[str]) -> None:
        """Raise exception for incompatible operations."""
        error_msg = i18n.t('components.processing.data_operations.errors.incompatible_operations',
                           operations=', '.join(operations))
        raise ValueError(error_msg)

    # Data transformation operations
    def select_keys(self, *, evaluate: bool | None = None) -> Data:
        """Select specific keys from the data dictionary."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.select_keys'))
            data_dict = self.get_normalized_data()
            filter_criteria: list[str] = self.select_keys_input

            # Filter the data
            if len(filter_criteria) == 1 and filter_criteria[0] == "data":
                filtered = data_dict["data"]
            else:
                if not all(key in data_dict for key in filter_criteria):
                    available_keys = ', '.join(list(data_dict.keys()))
                    error_msg = i18n.t('components.processing.data_operations.errors.select_key_not_found',
                                       available_keys=available_keys)
                    raise ValueError(error_msg)
                filtered = {key: value for key,
                            value in data_dict.items() if key in filter_criteria}

            # Create a new Data object with the filtered data
            if evaluate:
                filtered = self.recursive_eval(filtered)

            success_msg = i18n.t('components.processing.data_operations.success.keys_selected',
                                 count=len(filtered))
            self.status = success_msg
            return Data(data=filtered)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.select_keys_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def remove_keys(self) -> Data:
        """Remove specified keys from the data dictionary, recursively."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.remove_keys'))
            data_dict = self.get_normalized_data()
            remove_keys_input: list[str] = self.remove_keys_input

            filtered = DataOperationsComponent.remove_keys_recursive(
                data_dict, set(remove_keys_input))

            success_msg = i18n.t('components.processing.data_operations.success.keys_removed',
                                 count=len(remove_keys_input))
            self.status = success_msg
            return Data(data=filtered)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.remove_keys_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def rename_keys(self) -> Data:
        """Rename keys in the data dictionary, recursively."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.rename_keys'))
            data_dict = self.get_normalized_data()
            rename_keys_input: dict[str, str] = self.rename_keys_input

            renamed = DataOperationsComponent.rename_keys_recursive(
                data_dict, rename_keys_input)

            success_msg = i18n.t('components.processing.data_operations.success.keys_renamed',
                                 count=len(rename_keys_input))
            self.status = success_msg
            return Data(data=renamed)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.rename_keys_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def recursive_eval(self, data: Any) -> Any:
        """Recursively evaluate string values in a dictionary or list."""
        if isinstance(data, dict):
            return {k: self.recursive_eval(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.recursive_eval(item) for item in data]
        if isinstance(data, str):
            try:
                # Only attempt to evaluate strings that look like Python literals
                if (
                    data.strip().startswith(("{", "[", "(", "'", '"'))
                    or data.strip().lower() in ("true", "false", "none")
                    or data.strip().replace(".", "").isdigit()
                ):
                    return ast.literal_eval(data)
            except (ValueError, SyntaxError, TypeError, MemoryError):
                # If evaluation fails for any reason, return the original string
                return data
            return data
        return data

    def evaluate_data(self) -> Data:
        """Evaluate string values in the data dictionary."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.literal_eval'))
            logger.info("evaluating data")

            result = Data(**self.recursive_eval(self.get_data_dict()))

            success_msg = i18n.t(
                'components.processing.data_operations.success.data_evaluated')
            self.status = success_msg
            return result

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.evaluate_data_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def combine_data(self, *, evaluate: bool | None = None) -> Data:
        """Combine multiple data objects into one."""
        try:
            logger.info("combining data")
            if not self.data_is_list():
                return self.data[0] if self.data else Data(data={})

            if len(self.data) == 1:
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.combine_requires_multiple')
                raise ValueError(error_msg)

            data_dicts = [data.model_dump().get("data", data.model_dump())
                          for data in self.data]
            combined_data = {}

            for data_dict in data_dicts:
                for key, value in data_dict.items():
                    if key not in combined_data:
                        combined_data[key] = value
                    elif isinstance(combined_data[key], list):
                        if isinstance(value, list):
                            combined_data[key].extend(value)
                        else:
                            combined_data[key].append(value)
                    else:
                        # If current value is not a list, convert it to list and add new value
                        combined_data[key] = (
                            [combined_data[key], value] if not isinstance(
                                value, list) else [combined_data[key], *value]
                        )

            if evaluate:
                combined_data = self.recursive_eval(combined_data)

            success_msg = i18n.t('components.processing.data_operations.success.data_combined',
                                 count=len(self.data))
            self.status = success_msg
            return Data(**combined_data)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.combine_data_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def filter_data(self, input_data: list[dict[str, Any]], filter_key: str, filter_value: str, operator: str) -> list:
        """Filter list data based on key, value, and operator."""
        # Validate inputs
        if not input_data:
            warning_msg = i18n.t(
                'components.processing.data_operations.warnings.empty_input_data')
            self.status = warning_msg
            return []

        if not filter_key or not filter_value:
            warning_msg = i18n.t(
                'components.processing.data_operations.warnings.missing_filter_params')
            self.status = warning_msg
            return input_data

        # Filter the data
        filtered_data = []
        missing_key_count = 0

        for item in input_data:
            if isinstance(item, dict) and filter_key in item:
                if self.compare_values(item[filter_key], filter_value, operator):
                    filtered_data.append(item)
            else:
                missing_key_count += 1

        if missing_key_count > 0:
            warning_msg = i18n.t('components.processing.data_operations.warnings.items_missing_key',
                                 count=missing_key_count, key=filter_key)
            self.status = warning_msg

        return filtered_data

    def compare_values(self, item_value: Any, filter_value: str, operator: str) -> bool:
        # Map localized operator names to English for internal logic
        operator_map = {
            i18n.t('components.processing.data_operations.operator.equals'): "equals",
            i18n.t('components.processing.data_operations.operator.not_equals'): "not equals",
            i18n.t('components.processing.data_operations.operator.contains'): "contains",
            i18n.t('components.processing.data_operations.operator.starts_with'): "starts with",
            i18n.t('components.processing.data_operations.operator.ends_with'): "ends with",
        }

        # Use mapped operator or fall back to original
        internal_operator = operator_map.get(operator, operator)
        comparison_func = OPERATORS.get(internal_operator)

        if comparison_func:
            return comparison_func(item_value, filter_value)
        return False

    def multi_filter_data(self) -> Data:
        """Apply multiple filters to the data."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.filter_values'))
            data_filtered = self.get_normalized_data()

            for filter_key in self.filter_key:
                if filter_key not in data_filtered:
                    available_keys = ', '.join(list(data_filtered.keys()))
                    error_msg = i18n.t('components.processing.data_operations.errors.filter_key_not_found',
                                       key=filter_key, available_keys=available_keys)
                    raise ValueError(error_msg)

                if isinstance(data_filtered[filter_key], list):
                    for filter_data in self.filter_values:
                        filter_value = self.filter_values.get(filter_data)
                        if filter_value is not None:
                            data_filtered[filter_key] = self.filter_data(
                                input_data=data_filtered[filter_key],
                                filter_key=filter_data,
                                filter_value=filter_value,
                                operator=self.operator,
                            )
                else:
                    error_msg = i18n.t('components.processing.data_operations.errors.filter_key_not_list',
                                       key=filter_key)
                    raise TypeError(error_msg)

            success_msg = i18n.t(
                'components.processing.data_operations.success.data_filtered')
            self.status = success_msg
            return Data(**data_filtered)

        except (ValueError, TypeError):
            # Re-raise as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.filter_data_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def append_update(self) -> Data:
        """Append or Update with new key-value pairs."""
        try:
            self.validate_single_data(
                i18n.t('components.processing.data_operations.operations.append_update'))
            data_filtered = self.get_normalized_data()

            for key, value in self.append_update_data.items():
                data_filtered[key] = value

            success_msg = i18n.t('components.processing.data_operations.success.data_updated',
                                 count=len(self.append_update_data))
            self.status = success_msg
            return Data(**data_filtered)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.append_update_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    # Configuration and execution methods
    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None) -> dotdict:
        if field_name == "operations":
            build_config["operations"]["value"] = field_value
            selected_actions = [action["name"] for action in field_value]
            if len(selected_actions) == 1:
                # Map localized action names to internal names
                action_map = {
                    i18n.t('components.processing.data_operations.operations.select_keys'): "Select Keys",
                    i18n.t('components.processing.data_operations.operations.literal_eval'): "Literal Eval",
                    i18n.t('components.processing.data_operations.operations.combine'): "Combine",
                    i18n.t('components.processing.data_operations.operations.filter_values'): "Filter Values",
                    i18n.t('components.processing.data_operations.operations.append_update'): "Append or Update",
                    i18n.t('components.processing.data_operations.operations.remove_keys'): "Remove Keys",
                    i18n.t('components.processing.data_operations.operations.rename_keys'): "Rename Keys",
                    i18n.t('components.processing.data_operations.operations.path_selection'): "Path Selection",
                    i18n.t('components.processing.data_operations.operations.jq_expression'): "JQ Expression",
                }

                internal_action = action_map.get(
                    selected_actions[0], selected_actions[0])

                if internal_action in ACTION_CONFIG:
                    config = ACTION_CONFIG[internal_action]
                    build_config["data"]["is_list"] = config["is_list"]
                    logger.info(config["log_msg"])
                    return set_current_fields(
                        build_config=build_config,
                        action_fields=self.actions_data,
                        selected_action=internal_action,
                        default_fields=["operations", "data"],
                        func=set_field_display,
                    )

        if field_name == "mapped_json_display":
            try:
                parsed_json = json.loads(field_value)
                keys = DataOperationsComponent.extract_all_paths(parsed_json)
                build_config["selected_key"]["options"] = keys
                build_config["selected_key"]["show"] = True
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.json_parse_error', error=str(e))
                logger.error(error_msg)
                build_config["selected_key"]["show"] = False

        return build_config

    def json_path(self) -> Data:
        """Extract data using JSON path selection."""
        try:
            if not self.data or not self.selected_key:
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.missing_data_or_key')
                raise ValueError(error_msg)

            input_payload = self.data[0].data if isinstance(
                self.data, list) else self.data.data
            compiled = jq.compile(self.selected_key)
            result = compiled.input(input_payload).first()

            if isinstance(result, dict):
                success_msg = i18n.t(
                    'components.processing.data_operations.success.path_selection_executed')
                self.status = success_msg
                return Data(data=result)

            success_msg = i18n.t(
                'components.processing.data_operations.success.path_selection_executed')
            self.status = success_msg
            return Data(data={"result": result})

        except (ValueError, TypeError, KeyError) as e:
            error_msg = i18n.t(
                'components.processing.data_operations.errors.path_selection_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": str(e)})

    def as_data(self) -> Data:
        """Execute the selected data operation."""
        try:
            if not hasattr(self, "operations") or not self.operations:
                warning_msg = i18n.t(
                    'components.processing.data_operations.warnings.no_operations_selected')
                self.status = warning_msg
                return Data(data={})

            selected_actions = [action["name"] for action in self.operations]
            logger.info(f"selected_actions: {selected_actions}")

            if len(selected_actions) != 1:
                error_msg = i18n.t(
                    'components.processing.data_operations.errors.single_operation_required')
                self.status = error_msg
                return Data(data={})

            # Map localized action names to internal method names
            action_map: dict[str, str] = {
                i18n.t('components.processing.data_operations.operations.select_keys'): "select_keys",
                i18n.t('components.processing.data_operations.operations.literal_eval'): "evaluate_data",
                i18n.t('components.processing.data_operations.operations.combine'): "combine_data",
                i18n.t('components.processing.data_operations.operations.filter_values'): "multi_filter_data",
                i18n.t('components.processing.data_operations.operations.append_update'): "append_update",
                i18n.t('components.processing.data_operations.operations.remove_keys'): "remove_keys",
                i18n.t('components.processing.data_operations.operations.rename_keys'): "rename_keys",
                i18n.t('components.processing.data_operations.operations.path_selection'): "json_path",
                i18n.t('components.processing.data_operations.operations.jq_expression'): "json_query",
                # Also support English names for backwards compatibility
                "Select Keys": "select_keys",
                "Literal Eval": "evaluate_data",
                "Combine": "combine_data",
                "Filter Values": "multi_filter_data",
                "Append or Update": "append_update",
                "Remove Keys": "remove_keys",
                "Rename Keys": "rename_keys",
                "Path Selection": "json_path",
                "JQ Expression": "json_query",
            }

            method_name = action_map.get(selected_actions[0])
            if method_name and hasattr(self, method_name):
                handler = getattr(self, method_name)
                return handler()
            else:
                error_msg = i18n.t('components.processing.data_operations.errors.unknown_operation',
                                   operation=selected_actions[0])
                self.status = error_msg
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t('components.processing.data_operations.errors.operation_execution_failed',
                               error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            return Data(data={"error": error_msg})
