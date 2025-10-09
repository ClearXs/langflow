import re

import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MessageInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.message import Message


class ConditionalRouterComponent(Component):
    display_name = i18n.t('components.logic.conditional_router.display_name')
    description = i18n.t('components.logic.conditional_router.description')
    documentation: str = "https://docs.langflow.org/components-logic#conditional-router-if-else-component"
    icon = "split"
    name = "ConditionalRouter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__iteration_updated = False

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name=i18n.t(
                'components.logic.conditional_router.input_text.display_name'),
            info=i18n.t('components.logic.conditional_router.input_text.info'),
            required=True,
        ),
        DropdownInput(
            name="operator",
            display_name=i18n.t(
                'components.logic.conditional_router.operator.display_name'),
            options=[
                "equals",
                "not equals",
                "contains",
                "starts with",
                "ends with",
                "regex",
                "less than",
                "less than or equal",
                "greater than",
                "greater than or equal",
            ],
            info=i18n.t('components.logic.conditional_router.operator.info'),
            value="equals",
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="match_text",
            display_name=i18n.t(
                'components.logic.conditional_router.match_text.display_name'),
            info=i18n.t('components.logic.conditional_router.match_text.info'),
            required=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t(
                'components.logic.conditional_router.case_sensitive.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.case_sensitive.info'),
            value=True,
            advanced=True,
        ),
        MessageInput(
            name="true_case_message",
            display_name=i18n.t(
                'components.logic.conditional_router.true_case_message.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.true_case_message.info'),
            advanced=True,
        ),
        MessageInput(
            name="false_case_message",
            display_name=i18n.t(
                'components.logic.conditional_router.false_case_message.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.false_case_message.info'),
            advanced=True,
        ),
        IntInput(
            name="max_iterations",
            display_name=i18n.t(
                'components.logic.conditional_router.max_iterations.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.max_iterations.info'),
            value=10,
            advanced=True,
        ),
        DropdownInput(
            name="default_route",
            display_name=i18n.t(
                'components.logic.conditional_router.default_route.display_name'),
            options=["true_result", "false_result"],
            info=i18n.t(
                'components.logic.conditional_router.default_route.info'),
            value="false_result",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.conditional_router.outputs.true_result.display_name'),
            name="true_result",
            method="true_response",
            group_outputs=True
        ),
        Output(
            display_name=i18n.t(
                'components.logic.conditional_router.outputs.false_result.display_name'),
            name="false_result",
            method="false_response",
            group_outputs=True
        ),
    ]

    def _pre_run_setup(self):
        self.__iteration_updated = False
        logger.debug(
            i18n.t('components.logic.conditional_router.logs.pre_run_setup'))

    def evaluate_condition(self, input_text: str, match_text: str, operator: str, *, case_sensitive: bool) -> bool:
        logger.debug(i18n.t('components.logic.conditional_router.logs.evaluating',
                            operator=operator,
                            case_sensitive=case_sensitive))

        if not case_sensitive and operator != "regex":
            input_text = input_text.lower()
            match_text = match_text.lower()

        result = False

        if operator == "equals":
            result = input_text == match_text
        elif operator == "not equals":
            result = input_text != match_text
        elif operator == "contains":
            result = match_text in input_text
        elif operator == "starts with":
            result = input_text.startswith(match_text)
        elif operator == "ends with":
            result = input_text.endswith(match_text)
        elif operator == "regex":
            try:
                result = bool(re.match(match_text, input_text))
            except re.error as e:
                logger.warning(i18n.t('components.logic.conditional_router.warnings.invalid_regex',
                                      pattern=match_text,
                                      error=str(e)))
                return False
        elif operator in ["less than", "less than or equal", "greater than", "greater than or equal"]:
            try:
                input_num = float(input_text)
                match_num = float(match_text)
                if operator == "less than":
                    result = input_num < match_num
                elif operator == "less than or equal":
                    result = input_num <= match_num
                elif operator == "greater than":
                    result = input_num > match_num
                elif operator == "greater than or equal":
                    result = input_num >= match_num
            except ValueError as e:
                logger.warning(i18n.t('components.logic.conditional_router.warnings.invalid_number',
                                      input_text=input_text,
                                      match_text=match_text,
                                      error=str(e)))
                return False

        logger.debug(i18n.t('components.logic.conditional_router.logs.evaluation_result',
                            result=result))
        return result

    def iterate_and_stop_once(self, route_to_stop: str):
        """Handles cycle iteration counting and branch exclusion.

        Uses two complementary mechanisms:
        1. stop() - ACTIVE/INACTIVE state for cycle management (gets reset each iteration)
        2. exclude_branch_conditionally() - Persistent exclusion for conditional routing

        When max_iterations is reached, breaks the cycle by allowing the default_route to execute.
        """
        if not self.__iteration_updated:
            current_iteration = self.ctx.get(f"{self._id}_iteration", 0) + 1
            self.update_ctx({f"{self._id}_iteration": current_iteration})
            self.__iteration_updated = True

            logger.debug(i18n.t('components.logic.conditional_router.logs.iteration_updated',
                                iteration=current_iteration,
                                max_iterations=self.max_iterations))

            # Check if max iterations reached and we're trying to stop the default route
            if current_iteration >= self.max_iterations and route_to_stop == self.default_route:
                logger.info(i18n.t('components.logic.conditional_router.logs.max_iterations_reached',
                                   iteration=current_iteration,
                                   default_route=self.default_route))

                # Clear ALL conditional exclusions to allow default route to execute
                if self._id in self.graph.conditional_exclusion_sources:
                    previous_exclusions = self.graph.conditional_exclusion_sources[self._id]
                    self.graph.conditionally_excluded_vertices -= previous_exclusions
                    del self.graph.conditional_exclusion_sources[self._id]
                    logger.debug(i18n.t('components.logic.conditional_router.logs.cleared_exclusions',
                                        count=len(previous_exclusions)))

                # Switch which route to stop - stop the NON-default route to break the cycle
                route_to_stop = "true_result" if route_to_stop == "false_result" else "false_result"
                logger.debug(i18n.t('components.logic.conditional_router.logs.switched_route',
                                    new_route=route_to_stop))

                # Call stop to break the cycle
                self.stop(route_to_stop)
                # Don't apply conditional exclusion when breaking cycle
                return

            # Normal case: Use BOTH mechanisms
            logger.debug(i18n.t('components.logic.conditional_router.logs.stopping_route',
                                route=route_to_stop))

            # 1. stop() for cycle management (marks INACTIVE, updates run manager, gets reset)
            self.stop(route_to_stop)

            # 2. Conditional exclusion for persistent routing (doesn't get reset except by this router)
            self.graph.exclude_branch_conditionally(
                self._id, output_name=route_to_stop)

    def true_response(self) -> Message:
        result = self.evaluate_condition(
            self.input_text, self.match_text, self.operator, case_sensitive=self.case_sensitive
        )

        # Check if we should force output due to max_iterations on default route
        current_iteration = self.ctx.get(f"{self._id}_iteration", 0)
        force_output = current_iteration >= self.max_iterations and self.default_route == "true_result"

        if result or force_output:
            if force_output:
                self.status = i18n.t('components.logic.conditional_router.status.forced_true',
                                     iteration=current_iteration)
                logger.info(i18n.t('components.logic.conditional_router.logs.forced_true_output',
                                   iteration=current_iteration))
            else:
                self.status = i18n.t(
                    'components.logic.conditional_router.status.condition_true')
                logger.debug(
                    i18n.t('components.logic.conditional_router.logs.condition_true'))

            if not force_output:  # Only stop the other branch if not forcing due to max iterations
                self.iterate_and_stop_once("false_result")
            return self.true_case_message

        logger.debug(
            i18n.t('components.logic.conditional_router.logs.condition_false'))
        self.iterate_and_stop_once("true_result")
        return Message(content="")

    def false_response(self) -> Message:
        result = self.evaluate_condition(
            self.input_text, self.match_text, self.operator, case_sensitive=self.case_sensitive
        )

        # Check if we should force output due to max_iterations on default route
        current_iteration = self.ctx.get(f"{self._id}_iteration", 0)
        force_output = current_iteration >= self.max_iterations and self.default_route == "false_result"

        if not result or force_output:
            if force_output:
                self.status = i18n.t('components.logic.conditional_router.status.forced_false',
                                     iteration=current_iteration)
                logger.info(i18n.t('components.logic.conditional_router.logs.forced_false_output',
                                   iteration=current_iteration))
            else:
                self.status = i18n.t(
                    'components.logic.conditional_router.status.condition_false')
                logger.debug(
                    i18n.t('components.logic.conditional_router.logs.condition_false'))

            self.iterate_and_stop_once("true_result")
            return self.false_case_message

        logger.debug(
            i18n.t('components.logic.conditional_router.logs.condition_true'))
        self.iterate_and_stop_once("false_result")
        return Message(content="")

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        if field_name == "operator":
            logger.debug(i18n.t('components.logic.conditional_router.logs.updating_config',
                                operator=field_value))

            if field_value == "regex":
                build_config.pop("case_sensitive", None)
                logger.debug(
                    i18n.t('components.logic.conditional_router.logs.removed_case_sensitive'))
            elif "case_sensitive" not in build_config:
                case_sensitive_input = next(
                    (input_field for input_field in self.inputs if input_field.name ==
                     "case_sensitive"), None
                )
                if case_sensitive_input:
                    build_config["case_sensitive"] = case_sensitive_input.to_dict()
                    logger.debug(
                        i18n.t('components.logic.conditional_router.logs.added_case_sensitive'))
        return build_config
