from typing import Any

import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict


class DataConditionalRouterComponent(Component):
    display_name = i18n.t(
        'components.logic.data_conditional_router.display_name')
    description = i18n.t(
        'components.logic.data_conditional_router.description')
    icon = "split"
    name = "DataConditionalRouter"
    legacy = True
    replacement = ["logic.ConditionalRouter"]

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.logic.data_conditional_router.data_input.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.data_input.info'),
            is_list=True,
        ),
        MessageTextInput(
            name="key_name",
            display_name=i18n.t(
                'components.logic.data_conditional_router.key_name.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.key_name.info'),
        ),
        DropdownInput(
            name="operator",
            display_name=i18n.t(
                'components.logic.data_conditional_router.operator.display_name'),
            options=["equals", "not equals", "contains",
                     "starts with", "ends with", "boolean validator"],
            info=i18n.t(
                'components.logic.data_conditional_router.operator.info'),
            value="equals",
        ),
        MessageTextInput(
            name="compare_value",
            display_name=i18n.t(
                'components.logic.data_conditional_router.compare_value.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.compare_value.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.data_conditional_router.outputs.true_output.display_name'),
            name="true_output",
            method="process_data"
        ),
        Output(
            display_name=i18n.t(
                'components.logic.data_conditional_router.outputs.false_output.display_name'),
            name="false_output",
            method="process_data"
        ),
    ]

    def compare_values(self, item_value: str, compare_value: str, operator: str) -> bool:
        logger.debug(i18n.t('components.logic.data_conditional_router.logs.comparing',
                            operator=operator,
                            item_value=item_value,
                            compare_value=compare_value))

        result = False
        if operator == "equals":
            result = item_value == compare_value
        elif operator == "not equals":
            result = item_value != compare_value
        elif operator == "contains":
            result = compare_value in item_value
        elif operator == "starts with":
            result = item_value.startswith(compare_value)
        elif operator == "ends with":
            result = item_value.endswith(compare_value)
        elif operator == "boolean validator":
            result = self.parse_boolean(item_value)

        logger.debug(i18n.t('components.logic.data_conditional_router.logs.comparison_result',
                            result=result))
        return result

    def parse_boolean(self, value):
        logger.debug(i18n.t('components.logic.data_conditional_router.logs.parsing_boolean',
                            value=value,
                            value_type=type(value).__name__))

        result = False
        if isinstance(value, bool):
            result = value
        elif isinstance(value, str):
            result = value.lower() in {"true", "1", "yes", "y", "on"}
        else:
            result = bool(value)

        logger.debug(i18n.t('components.logic.data_conditional_router.logs.boolean_result',
                            result=result))
        return result

    def validate_input(self, data_item: Data) -> bool:
        logger.debug(
            i18n.t('components.logic.data_conditional_router.logs.validating_input'))

        if not isinstance(data_item, Data):
            error_msg = i18n.t(
                'components.logic.data_conditional_router.errors.not_data_object')
            self.status = error_msg
            logger.warning(error_msg)
            return False

        if self.key_name not in data_item.data:
            error_msg = i18n.t('components.logic.data_conditional_router.errors.key_not_found',
                               key=self.key_name)
            self.status = error_msg
            logger.warning(error_msg)
            return False

        logger.debug(
            i18n.t('components.logic.data_conditional_router.logs.validation_passed'))
        return True

    def process_data(self) -> Data | list[Data]:
        try:
            if isinstance(self.data_input, list):
                logger.info(i18n.t('components.logic.data_conditional_router.logs.processing_list',
                                   count=len(self.data_input)))

                true_output = []
                false_output = []
                for item in self.data_input:
                    if self.validate_input(item):
                        result = self.process_single_data(item)
                        if result:
                            true_output.append(item)
                        else:
                            false_output.append(item)

                logger.info(i18n.t('components.logic.data_conditional_router.logs.list_results',
                                   true_count=len(true_output),
                                   false_count=len(false_output)))

                self.stop("false_output" if true_output else "true_output")
                return true_output or false_output

            logger.debug(
                i18n.t('components.logic.data_conditional_router.logs.processing_single'))

            if not self.validate_input(self.data_input):
                error_data = Data(data={"error": self.status})
                logger.error(i18n.t('components.logic.data_conditional_router.logs.validation_failed',
                                    error=self.status))
                return error_data

            result = self.process_single_data(self.data_input)
            self.stop("false_output" if result else "true_output")
            return self.data_input

        except Exception as e:
            error_msg = i18n.t('components.logic.data_conditional_router.errors.processing_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})

    def process_single_data(self, data_item: Data) -> bool:
        item_value = data_item.data[self.key_name]
        operator = self.operator

        logger.debug(i18n.t('components.logic.data_conditional_router.logs.processing_item',
                            key=self.key_name,
                            value=item_value,
                            operator=operator))

        if operator == "boolean validator":
            condition_met = self.parse_boolean(item_value)
            condition_description = i18n.t('components.logic.data_conditional_router.conditions.boolean_validation',
                                           key=self.key_name)
        else:
            compare_value = self.compare_value
            condition_met = self.compare_values(
                str(item_value), compare_value, operator)
            condition_description = i18n.t('components.logic.data_conditional_router.conditions.comparison',
                                           key=self.key_name,
                                           operator=operator,
                                           value=compare_value)

        if condition_met:
            status_msg = i18n.t('components.logic.data_conditional_router.status.condition_met',
                                description=condition_description)
            self.status = status_msg
            logger.info(status_msg)
            return True

        status_msg = i18n.t('components.logic.data_conditional_router.status.condition_not_met',
                            description=condition_description)
        self.status = status_msg
        logger.info(status_msg)
        return False

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name == "operator":
            logger.debug(i18n.t('components.logic.data_conditional_router.logs.updating_config',
                                operator=field_value))

            if field_value == "boolean validator":
                build_config["compare_value"]["show"] = False
                build_config["compare_value"]["advanced"] = True
                build_config["compare_value"]["value"] = None
                logger.debug(
                    i18n.t('components.logic.data_conditional_router.logs.hidden_compare_value'))
            else:
                build_config["compare_value"]["show"] = True
                build_config["compare_value"]["advanced"] = False
                logger.debug(
                    i18n.t('components.logic.data_conditional_router.logs.shown_compare_value'))

        return build_config
