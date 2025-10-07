from typing import Any, Dict, List, Optional, Union, Iterator, Callable
import time
import json
from datetime import datetime, timedelta
from itertools import islice
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    MultilineInput,
    IntInput,
    FloatInput
)
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.template.field.base import Output


class LoopComponent(Component):
    display_name = i18n.t('components.logic.loop.display_name')
    description = i18n.t('components.logic.loop.description')
    documentation: str = "https://docs.langflow.org/components-logic#loop"
    icon = "Repeat"
    name = "Loop"

    inputs = [
        DropdownInput(
            name="loop_type",
            display_name=i18n.t(
                'components.logic.loop.loop_type.display_name'),
            info=i18n.t('components.logic.loop.loop_type.info'),
            options=["for_each", "while", "range", "until", "infinite"],
            value="for_each",
            required=True,
        ),
        HandleInput(
            name="input_data",
            display_name=i18n.t(
                'components.logic.loop.input_data.display_name'),
            info=i18n.t('components.logic.loop.input_data.info'),
            input_types=["Data", "Message", "Text", "Any"],
            required=True,
        ),
        MultilineInput(
            name="loop_condition",
            display_name=i18n.t(
                'components.logic.loop.loop_condition.display_name'),
            info=i18n.t('components.logic.loop.loop_condition.info'),
            placeholder='{\n  "condition": "item > 0",\n  "max_iterations": 100\n}',
        ),
        IntInput(
            name="range_start",
            display_name=i18n.t(
                'components.logic.loop.range_start.display_name'),
            info=i18n.t('components.logic.loop.range_start.info'),
            value=0,
            advanced=True,
        ),
        IntInput(
            name="range_end",
            display_name=i18n.t(
                'components.logic.loop.range_end.display_name'),
            info=i18n.t('components.logic.loop.range_end.info'),
            value=10,
            advanced=True,
        ),
        IntInput(
            name="range_step",
            display_name=i18n.t(
                'components.logic.loop.range_step.display_name'),
            info=i18n.t('components.logic.loop.range_step.info'),
            value=1,
            range_spec=(1, 1000),
            advanced=True,
        ),
        IntInput(
            name="max_iterations",
            display_name=i18n.t(
                'components.logic.loop.max_iterations.display_name'),
            info=i18n.t('components.logic.loop.max_iterations.info'),
            value=100,
            range_spec=(1, 10000),
            advanced=True,
        ),
        FloatInput(
            name="delay_between_iterations",
            display_name=i18n.t(
                'components.logic.loop.delay_between_iterations.display_name'),
            info=i18n.t('components.logic.loop.delay_between_iterations.info'),
            value=0.0,
            range_spec=(0.0, 60.0),
            advanced=True,
        ),
        BoolInput(
            name="break_on_error",
            display_name=i18n.t(
                'components.logic.loop.break_on_error.display_name'),
            info=i18n.t('components.logic.loop.break_on_error.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="collect_results",
            display_name=i18n.t(
                'components.logic.loop.collect_results.display_name'),
            info=i18n.t('components.logic.loop.collect_results.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="output_mode",
            display_name=i18n.t(
                'components.logic.loop.output_mode.display_name'),
            info=i18n.t('components.logic.loop.output_mode.info'),
            options=["all_results", "last_result", "aggregated", "streaming"],
            value="all_results",
            advanced=True,
        ),
        BoolInput(
            name="include_index",
            display_name=i18n.t(
                'components.logic.loop.include_index.display_name'),
            info=i18n.t('components.logic.loop.include_index.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="parallel_execution",
            display_name=i18n.t(
                'components.logic.loop.parallel_execution.display_name'),
            info=i18n.t('components.logic.loop.parallel_execution.info'),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t(
                'components.logic.loop.batch_size.display_name'),
            info=i18n.t('components.logic.loop.batch_size.info'),
            value=1,
            range_spec=(1, 1000),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.loop.outputs.loop_results.display_name'),
            name="loop_results",
            method="execute_loop",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.loop.outputs.loop_stats.display_name'),
            name="loop_stats",
            method="get_loop_stats",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.loop.outputs.current_item.display_name'),
            name="current_item",
            method="get_current_item",
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop_stats = {
            "total_iterations": 0,
            "successful_iterations": 0,
            "failed_iterations": 0,
            "start_time": None,
            "end_time": None,
            "errors": [],
        }
        self._current_item = None
        self._current_index = 0

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "loop_type":
            if field_value == "range":
                build_config["range_start"]["show"] = True
                build_config["range_end"]["show"] = True
                build_config["range_step"]["show"] = True
                build_config["loop_condition"]["show"] = False
            elif field_value in ["while", "until"]:
                build_config["range_start"]["show"] = False
                build_config["range_end"]["show"] = False
                build_config["range_step"]["show"] = False
                build_config["loop_condition"]["show"] = True
            elif field_value == "for_each":
                build_config["range_start"]["show"] = False
                build_config["range_end"]["show"] = False
                build_config["range_step"]["show"] = False
                build_config["loop_condition"]["show"] = False
            elif field_value == "infinite":
                build_config["max_iterations"]["show"] = True
                build_config["loop_condition"]["show"] = True

        if field_name == "parallel_execution":
            if field_value:
                build_config["batch_size"]["show"] = True
                build_config["delay_between_iterations"]["show"] = False
            else:
                build_config["batch_size"]["show"] = False
                build_config["delay_between_iterations"]["show"] = True

        if field_name == "collect_results":
            if not field_value:
                build_config["output_mode"]["options"] = [
                    "last_result", "streaming"]
            else:
                build_config["output_mode"]["options"] = [
                    "all_results", "last_result", "aggregated", "streaming"]

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        if self.loop_type == "range":
            if self.range_start >= self.range_end:
                error_message = i18n.t(
                    'components.logic.loop.errors.invalid_range')
                self.status = error_message
                raise ValueError(error_message)

            if self.range_step <= 0:
                error_message = i18n.t(
                    'components.logic.loop.errors.invalid_step')
                self.status = error_message
                raise ValueError(error_message)

        if self.max_iterations <= 0:
            error_message = i18n.t(
                'components.logic.loop.errors.invalid_max_iterations')
            self.status = error_message
            raise ValueError(error_message)

        if self.delay_between_iterations < 0:
            error_message = i18n.t(
                'components.logic.loop.errors.invalid_delay')
            self.status = error_message
            raise ValueError(error_message)

        if self.batch_size <= 0:
            error_message = i18n.t(
                'components.logic.loop.errors.invalid_batch_size')
            self.status = error_message
            raise ValueError(error_message)

        if self.loop_condition:
            try:
                json.loads(self.loop_condition)
            except json.JSONDecodeError as e:
                error_message = i18n.t('components.logic.loop.errors.invalid_loop_condition',
                                       error=str(e))
                self.status = error_message
                raise ValueError(error_message) from e

    def _parse_loop_condition(self) -> Optional[Dict[str, Any]]:
        """Parse loop condition from JSON."""
        if not self.loop_condition:
            return None

        try:
            return json.loads(self.loop_condition)
        except json.JSONDecodeError:
            return None

    def _evaluate_condition(self, item: Any, index: int, condition_dict: Dict[str, Any]) -> bool:
        """Evaluate loop condition."""
        try:
            condition_str = condition_dict.get("condition", "True")

            # Create evaluation context
            context = {
                'item': item,
                'index': index,
                'current_item': item,
                'current_index': index,
                'iteration': index,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
            }

            # Add item properties to context if it's a dict
            if isinstance(item, dict):
                context.update(item)
            elif isinstance(item, Data) and hasattr(item, 'data'):
                if isinstance(item.data, dict):
                    context.update(item.data)

            # Evaluate condition
            result = eval(condition_str, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            warning_message = i18n.t('components.logic.loop.warnings.condition_evaluation_error',
                                     condition=condition_str, error=str(e))
            self.status = warning_message
            return False

    def _get_iteration_data(self) -> Iterator[Any]:
        """Get iterator for loop data based on loop type."""
        if self.loop_type == "for_each":
            if isinstance(self.input_data, list):
                return iter(self.input_data)
            elif isinstance(self.input_data, Data) and hasattr(self.input_data, 'data'):
                if isinstance(self.input_data.data, list):
                    return iter(self.input_data.data)
                else:
                    return iter([self.input_data.data])
            else:
                return iter([self.input_data])

        elif self.loop_type == "range":
            return iter(range(self.range_start, self.range_end, self.range_step))

        elif self.loop_type in ["while", "until", "infinite"]:
            # Generate infinite sequence, will be controlled by condition
            count = 0
            while count < self.max_iterations:
                yield self.input_data
                count += 1

        else:
            error_message = i18n.t('components.logic.loop.errors.unsupported_loop_type',
                                   type=self.loop_type)
            raise ValueError(error_message)

    def _process_single_item(self, item: Any, index: int) -> Any:
        """Process a single item in the loop."""
        try:
            self._current_item = item
            self._current_index = index

            # In a real implementation, this would execute the connected nodes
            # For now, we'll return a processed version of the item
            if isinstance(item, dict):
                processed_item = {
                    **item,
                    "loop_index": index,
                    "processed_at": datetime.now().isoformat(),
                }
            elif isinstance(item, Data):
                processed_data = item.data.copy() if hasattr(
                    item, 'data') and isinstance(item.data, dict) else {"value": item}
                processed_data.update({
                    "loop_index": index,
                    "processed_at": datetime.now().isoformat(),
                })
                processed_item = Data(data=processed_data)
            else:
                processed_item = {
                    "original_value": item,
                    "loop_index": index,
                    "processed_at": datetime.now().isoformat(),
                }

            if self.include_index:
                if isinstance(processed_item, dict):
                    processed_item["index"] = index
                elif isinstance(processed_item, Data) and hasattr(processed_item, 'data'):
                    processed_item.data["index"] = index

            self._loop_stats["successful_iterations"] += 1
            return processed_item

        except Exception as e:
            self._loop_stats["failed_iterations"] += 1
            error_info = {
                "item": str(item),
                "index": index,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            self._loop_stats["errors"].append(error_info)

            if self.break_on_error:
                error_message = i18n.t('components.logic.loop.errors.processing_error',
                                       index=index, error=str(e))
                raise ValueError(error_message) from e
            else:
                warning_message = i18n.t('components.logic.loop.warnings.item_processing_error',
                                         index=index, error=str(e))
                self.status = warning_message
                return None

    def _process_batch(self, batch: List[Any], start_index: int) -> List[Any]:
        """Process a batch of items."""
        results = []
        for i, item in enumerate(batch):
            result = self._process_single_item(item, start_index + i)
            if result is not None:
                results.append(result)
        return results

    def _aggregate_results(self, results: List[Any]) -> Any:
        """Aggregate loop results based on output mode."""
        if not results:
            return Data(data={"message": "No results", "count": 0})

        if self.output_mode == "all_results":
            return results

        elif self.output_mode == "last_result":
            return results[-1] if results else None

        elif self.output_mode == "aggregated":
            # Create aggregated result
            aggregated = {
                "total_items": len(results),
                "first_item": results[0] if results else None,
                "last_item": results[-1] if results else None,
                "successful_count": self._loop_stats["successful_iterations"],
                "failed_count": self._loop_stats["failed_iterations"],
                "aggregated_at": datetime.now().isoformat(),
            }

            # Try to aggregate numeric values
            numeric_values = []
            for result in results:
                if isinstance(result, (int, float)):
                    numeric_values.append(result)
                elif isinstance(result, dict) and "value" in result:
                    try:
                        numeric_values.append(float(result["value"]))
                    except (ValueError, TypeError):
                        pass

            if numeric_values:
                aggregated.update({
                    "sum": sum(numeric_values),
                    "average": sum(numeric_values) / len(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "count": len(numeric_values),
                })

            return Data(data=aggregated)

        elif self.output_mode == "streaming":
            # Return generator for streaming
            return (result for result in results)

        else:
            return results

    def execute_loop(self) -> Any:
        """Execute the main loop logic."""
        try:
            self._validate_inputs()

            # Initialize stats
            self._loop_stats = {
                "total_iterations": 0,
                "successful_iterations": 0,
                "failed_iterations": 0,
                "start_time": datetime.now(),
                "end_time": None,
                "errors": [],
            }

            # Get loop condition
            condition_dict = self._parse_loop_condition()

            # Get iteration data
            iteration_data = self._get_iteration_data()
            results = []

            # Execute loop
            for index, item in enumerate(iteration_data):
                if index >= self.max_iterations:
                    warning_message = i18n.t('components.logic.loop.warnings.max_iterations_reached',
                                             max_iterations=self.max_iterations)
                    self.status = warning_message
                    break

                # Check loop condition
                if condition_dict:
                    if self.loop_type == "while":
                        if not self._evaluate_condition(item, index, condition_dict):
                            break
                    elif self.loop_type == "until":
                        if self._evaluate_condition(item, index, condition_dict):
                            break

                self._loop_stats["total_iterations"] += 1

                # Process item
                if self.parallel_execution and self.batch_size > 1:
                    # Collect batch
                    batch = [item]
                    try:
                        for _ in range(self.batch_size - 1):
                            batch.append(next(iteration_data))
                            self._loop_stats["total_iterations"] += 1
                    except StopIteration:
                        pass

                    batch_results = self._process_batch(batch, index)
                    if self.collect_results:
                        results.extend(batch_results)
                else:
                    result = self._process_single_item(item, index)
                    if result is not None and self.collect_results:
                        results.append(result)

                # Add delay if specified
                if self.delay_between_iterations > 0:
                    time.sleep(self.delay_between_iterations)

            # Finalize stats
            self._loop_stats["end_time"] = datetime.now()
            duration = (
                self._loop_stats["end_time"] - self._loop_stats["start_time"]).total_seconds()

            # Aggregate results
            final_result = self._aggregate_results(results)

            success_message = i18n.t('components.logic.loop.success.loop_completed',
                                     iterations=self._loop_stats["total_iterations"],
                                     duration=duration)
            self.status = success_message

            return final_result

        except Exception as e:
            self._loop_stats["end_time"] = datetime.now()
            error_message = i18n.t(
                'components.logic.loop.errors.loop_execution_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_loop_stats(self) -> Data:
        """Get loop execution statistics."""
        try:
            stats = self._loop_stats.copy()

            if stats["start_time"]:
                stats["start_time"] = stats["start_time"].isoformat()
            if stats["end_time"]:
                stats["end_time"] = stats["end_time"].isoformat()
                duration = (datetime.fromisoformat(stats["end_time"]) -
                            datetime.fromisoformat(stats["start_time"])).total_seconds()
                stats["duration_seconds"] = duration
                stats["iterations_per_second"] = (
                    stats["total_iterations"] / duration if duration > 0 else 0
                )

            stats.update({
                "loop_type": self.loop_type,
                "max_iterations": self.max_iterations,
                "delay_between_iterations": self.delay_between_iterations,
                "break_on_error": self.break_on_error,
                "collect_results": self.collect_results,
                "output_mode": self.output_mode,
                "parallel_execution": self.parallel_execution,
                "batch_size": self.batch_size,
                "success_rate": (
                    stats["successful_iterations"] / stats["total_iterations"]
                    if stats["total_iterations"] > 0 else 0
                ),
            })

            return Data(data=stats)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.loop.errors.stats_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_current_item(self) -> Any:
        """Get the current item being processed."""
        try:
            if self._current_item is None:
                return Data(data={
                    "message": "No current item",
                    "current_index": self._current_index,
                    "timestamp": datetime.now().isoformat(),
                })

            current_data = {
                "current_item": self._current_item,
                "current_index": self._current_index,
                "loop_type": self.loop_type,
                "timestamp": datetime.now().isoformat(),
            }

            return Data(data=current_data)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.loop.errors.current_item_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
