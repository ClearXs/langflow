from typing import Any

import i18n
from langflow.custom import Component
from langflow.io import BoolInput, HandleInput, MessageInput, MessageTextInput, MultilineInput, Output, TableInput
from langflow.log.logger import logger
from langflow.schema.message import Message


class SmartRouterComponent(Component):
    display_name = i18n.t(
        'components.logic.llm_conditional_router.display_name')
    description = i18n.t('components.logic.llm_conditional_router.description')
    icon = "equal"
    name = "SmartRouter"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._matched_category = None

    inputs = [
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.llm.display_name'),
            info=i18n.t('components.logic.llm_conditional_router.llm.info'),
            input_types=["LanguageModel"],
            required=True,
        ),
        MessageTextInput(
            name="input_text",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.input_text.display_name'),
            info=i18n.t(
                'components.logic.llm_conditional_router.input_text.info'),
            required=True,
        ),
        TableInput(
            trigger_text=i18n.t(
                'components.inputs.input_mixin.open_table'),
            name="routes",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.routes.display_name'),
            info=i18n.t('components.logic.llm_conditional_router.routes.info'),
            table_schema=[
                {
                    "name": "route_category",
                    "display_name": i18n.t('components.logic.llm_conditional_router.routes.schema.route_category.display_name'),
                    "type": "str",
                    "description": i18n.t('components.logic.llm_conditional_router.routes.schema.route_category.description'),
                },
                {
                    "name": "output_value",
                    "display_name": i18n.t('components.logic.llm_conditional_router.routes.schema.output_value.display_name'),
                    "type": "str",
                    "description": i18n.t('components.logic.llm_conditional_router.routes.schema.output_value.description'),
                    "default": "",
                },
            ],
            value=[
                {"route_category": "Positive", "output_value": ""},
                {"route_category": "Negative", "output_value": ""},
            ],
            real_time_refresh=True,
            required=True,
        ),
        MessageInput(
            name="message",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.message.display_name'),
            info=i18n.t(
                'components.logic.llm_conditional_router.message.info'),
            required=False,
            advanced=True,
        ),
        BoolInput(
            name="enable_else_output",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.enable_else_output.display_name'),
            info=i18n.t(
                'components.logic.llm_conditional_router.enable_else_output.info'),
            value=False,
            advanced=True,
        ),
        MultilineInput(
            name="custom_prompt",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.custom_prompt.display_name'),
            info=i18n.t(
                'components.logic.llm_conditional_router.custom_prompt.info'),
            advanced=True,
        ),
    ]

    outputs: list[Output] = []

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Create a dynamic output for each category in the categories table."""
        if field_name in {"routes", "enable_else_output"}:
            logger.debug(i18n.t('components.logic.llm_conditional_router.logs.updating_outputs',
                                field_name=field_name))

            frontend_node["outputs"] = []

            # Get the routes data - either from field_value (if routes field) or from component state
            routes_data = field_value if field_name == "routes" else getattr(
                self, "routes", [])

            # Add a dynamic output for each category - all using the same method
            for i, row in enumerate(routes_data):
                route_category = row.get("route_category", f"Category {i + 1}")
                frontend_node["outputs"].append(
                    Output(
                        display_name=route_category,
                        name=f"category_{i + 1}_result",
                        method="process_case",
                        group_outputs=True,
                    )
                )
                logger.debug(i18n.t('components.logic.llm_conditional_router.logs.output_added',
                                    index=i + 1,
                                    category=route_category))

            # Add default output only if enabled
            if field_name == "enable_else_output":
                enable_else = field_value
            else:
                enable_else = getattr(self, "enable_else_output", False)

            if enable_else:
                frontend_node["outputs"].append(
                    Output(display_name="Else", name="default_result",
                           method="default_response", group_outputs=True)
                )
                logger.debug(
                    i18n.t('components.logic.llm_conditional_router.logs.else_output_added'))

            logger.info(i18n.t('components.logic.llm_conditional_router.logs.outputs_updated',
                               count=len(frontend_node["outputs"])))

        return frontend_node

    def process_case(self) -> Message:
        """Process all categories using LLM categorization and return message for matching category."""
        # Clear any previous match state
        self._matched_category = None
        logger.debug(
            i18n.t('components.logic.llm_conditional_router.logs.processing_started'))

        categories = getattr(self, "routes", [])
        input_text = getattr(self, "input_text", "")

        # Find the matching category using LLM-based categorization
        matched_category = None
        llm = getattr(self, "llm", None)

        if llm and categories:
            # Create prompt for categorization
            category_values = [
                category.get("route_category", f"Category {i + 1}") for i, category in enumerate(categories)
            ]
            categories_text = ", ".join(
                [f'"{cat}"' for cat in category_values if cat])

            # Create base prompt
            base_prompt = (
                f"You are a text classifier. Given the following text and categories, "
                f"determine which category best matches the text.\n\n"
                f'Text to classify: "{input_text}"\n\n'
                f"Available categories: {categories_text}\n\n"
                f"Respond with ONLY the exact category name that best matches the text. "
                f'If none match well, respond with "NONE".\n\n'
                f"Category:"
            )

            # Use custom prompt as additional instructions if provided
            custom_prompt = getattr(self, "custom_prompt", "")
            if custom_prompt and custom_prompt.strip():
                status_msg = i18n.t(
                    'components.logic.llm_conditional_router.status.using_custom_prompt')
                self.status = status_msg
                logger.info(status_msg)

                # Format custom prompt with variables
                formatted_custom = custom_prompt.format(
                    input_text=input_text, routes=categories_text)
                # Combine base prompt with custom instructions
                prompt = f"{base_prompt}\n\nAdditional Instructions:\n{formatted_custom}"
            else:
                status_msg = i18n.t(
                    'components.logic.llm_conditional_router.status.using_default_prompt')
                self.status = status_msg
                logger.info(status_msg)
                prompt = base_prompt

            # Log the final prompt being sent to LLM
            logger.debug(i18n.t('components.logic.llm_conditional_router.logs.prompt_sent',
                                prompt=prompt))
            self.status = i18n.t(
                'components.logic.llm_conditional_router.status.prompt_sent', prompt=prompt)

            try:
                # Use the LLM to categorize
                if hasattr(llm, "invoke"):
                    response = llm.invoke(prompt)
                    if hasattr(response, "content"):
                        categorization = response.content.strip().strip('"')
                    else:
                        categorization = str(response).strip().strip('"')
                else:
                    categorization = str(llm(prompt)).strip().strip('"')

                # Log the categorization process
                logger.info(i18n.t('components.logic.llm_conditional_router.logs.llm_response',
                                   response=categorization))
                self.status = i18n.t('components.logic.llm_conditional_router.status.llm_response',
                                     response=categorization)

                # Find matching category based on LLM response
                for i, category in enumerate(categories):
                    route_category = category.get("route_category", "")

                    # Log each comparison attempt
                    logger.debug(i18n.t('components.logic.llm_conditional_router.logs.comparing_category',
                                        response=categorization,
                                        index=i + 1,
                                        category=route_category))
                    self.status = i18n.t('components.logic.llm_conditional_router.status.comparing_category',
                                         response=categorization,
                                         index=i + 1,
                                         category=route_category)

                    if categorization.lower() == route_category.lower():
                        matched_category = i
                        logger.info(i18n.t('components.logic.llm_conditional_router.logs.match_found',
                                           index=i + 1,
                                           response=categorization))
                        self.status = i18n.t('components.logic.llm_conditional_router.status.match_found',
                                             index=i + 1,
                                             response=categorization)
                        break

                if matched_category is None:
                    available_cats = [category.get(
                        "route_category", "") for category in categories]
                    logger.warning(i18n.t('components.logic.llm_conditional_router.logs.no_match_found',
                                          response=categorization,
                                          categories=available_cats))
                    self.status = i18n.t('components.logic.llm_conditional_router.status.no_match_found',
                                         response=categorization,
                                         categories=available_cats)

            except RuntimeError as e:
                error_msg = i18n.t('components.logic.llm_conditional_router.errors.llm_categorization_failed',
                                   error=str(e))
                logger.exception(error_msg)
                self.status = error_msg
        else:
            warning_msg = i18n.t(
                'components.logic.llm_conditional_router.warnings.no_llm_provided')
            logger.warning(warning_msg)
            self.status = warning_msg

        if matched_category is not None:
            # Store the matched category for other outputs to check
            self._matched_category = matched_category

            # Stop all category outputs except the matched one
            for i in range(len(categories)):
                if i != matched_category:
                    self.stop(f"category_{i + 1}_result")

            # Also stop the default output (if it exists)
            enable_else = getattr(self, "enable_else_output", False)
            if enable_else:
                self.stop("default_result")

            route_category = categories[matched_category].get(
                "route_category", f"Category {matched_category + 1}")
            success_msg = i18n.t('components.logic.llm_conditional_router.status.categorized_as',
                                 category=route_category)
            logger.info(success_msg)
            self.status = success_msg

            # Check if there's an override output (takes precedence over everything)
            override_output = getattr(self, "message", None)
            if (
                override_output
                and hasattr(override_output, "text")
                and override_output.text
                and str(override_output.text).strip()
            ):
                logger.debug(
                    i18n.t('components.logic.llm_conditional_router.logs.using_override_output'))
                return Message(text=str(override_output.text))
            if override_output and isinstance(override_output, str) and override_output.strip():
                logger.debug(
                    i18n.t('components.logic.llm_conditional_router.logs.using_override_output'))
                return Message(text=str(override_output))

            # Check if there's a custom output value for this category
            custom_output = categories[matched_category].get(
                "output_value", "")
            # Treat None, empty string, or whitespace as blank
            if custom_output and str(custom_output).strip() and str(custom_output).strip().lower() != "none":
                # Use custom output value
                logger.debug(
                    i18n.t('components.logic.llm_conditional_router.logs.using_custom_output'))
                return Message(text=str(custom_output))

            # Use input as default output
            logger.debug(
                i18n.t('components.logic.llm_conditional_router.logs.using_input_as_output'))
            return Message(text=input_text)

        # No match found, stop all category outputs
        for i in range(len(categories)):
            self.stop(f"category_{i + 1}_result")

        # Check if else output is enabled
        enable_else = getattr(self, "enable_else_output", False)
        if enable_else:
            # The default_response will handle the else case
            logger.debug(
                i18n.t('components.logic.llm_conditional_router.logs.routing_to_else'))
            self.stop("process_case")
            return Message(text="")

        # No else output, so no output at all
        warning_msg = i18n.t(
            'components.logic.llm_conditional_router.warnings.no_match_no_else')
        logger.warning(warning_msg)
        self.status = warning_msg
        return Message(text="")

    def default_response(self) -> Message:
        """Handle the else case when no conditions match."""
        # Check if else output is enabled
        enable_else = getattr(self, "enable_else_output", False)
        if not enable_else:
            warning_msg = i18n.t(
                'components.logic.llm_conditional_router.warnings.else_output_disabled')
            logger.warning(warning_msg)
            self.status = warning_msg
            return Message(text="")

        # Clear any previous match state if not already set
        if not hasattr(self, "_matched_category"):
            self._matched_category = None

        categories = getattr(self, "routes", [])
        input_text = getattr(self, "input_text", "")

        # Check if a match was already found in process_case
        if hasattr(self, "_matched_category") and self._matched_category is not None:
            status_msg = i18n.t('components.logic.llm_conditional_router.status.match_already_found',
                                index=self._matched_category + 1)
            logger.info(status_msg)
            self.status = status_msg
            self.stop("default_result")
            return Message(text="")

        # Check if any category matches using LLM categorization
        has_match = False
        llm = getattr(self, "llm", None)

        if llm and categories:
            try:
                # Create prompt for categorization
                category_values = [
                    category.get("route_category", f"Category {i + 1}") for i, category in enumerate(categories)
                ]
                categories_text = ", ".join(
                    [f'"{cat}"' for cat in category_values if cat])

                # Create base prompt
                base_prompt = (
                    "You are a text classifier. Given the following text and categories, "
                    "determine which category best matches the text.\n\n"
                    f'Text to classify: "{input_text}"\n\n'
                    f"Available categories: {categories_text}\n\n"
                    "Respond with ONLY the exact category name that best matches the text. "
                    'If none match well, respond with "NONE".\n\n'
                    "Category:"
                )

                # Use custom prompt as additional instructions if provided
                custom_prompt = getattr(self, "custom_prompt", "")
                if custom_prompt and custom_prompt.strip():
                    status_msg = i18n.t(
                        'components.logic.llm_conditional_router.status.using_custom_prompt_default')
                    logger.info(status_msg)
                    self.status = status_msg

                    # Format custom prompt with variables
                    formatted_custom = custom_prompt.format(
                        input_text=input_text, routes=categories_text)
                    # Combine base prompt with custom instructions
                    prompt = f"{base_prompt}\n\nAdditional Instructions:\n{formatted_custom}"
                else:
                    status_msg = i18n.t(
                        'components.logic.llm_conditional_router.status.using_default_prompt_default')
                    logger.info(status_msg)
                    self.status = status_msg
                    prompt = base_prompt

                # Log the final prompt being sent to LLM for default check
                logger.debug(i18n.t('components.logic.llm_conditional_router.logs.default_check_prompt',
                                    prompt=prompt))
                self.status = i18n.t('components.logic.llm_conditional_router.status.default_check_prompt',
                                     prompt=prompt)

                # Use the LLM to categorize
                if hasattr(llm, "invoke"):
                    response = llm.invoke(prompt)
                    if hasattr(response, "content"):
                        categorization = response.content.strip().strip('"')
                    else:
                        categorization = str(response).strip().strip('"')
                else:
                    categorization = str(llm(prompt)).strip().strip('"')

                # Log the categorization process for default check
                logger.info(i18n.t('components.logic.llm_conditional_router.logs.default_check_response',
                                   response=categorization))
                self.status = i18n.t('components.logic.llm_conditional_router.status.default_check_response',
                                     response=categorization)

                # Check if LLM response matches any category
                for i, category in enumerate(categories):
                    route_category = category.get("route_category", "")

                    # Log each comparison attempt
                    logger.debug(i18n.t('components.logic.llm_conditional_router.logs.default_check_comparing',
                                        response=categorization,
                                        index=i + 1,
                                        category=route_category))
                    self.status = i18n.t('components.logic.llm_conditional_router.status.default_check_comparing',
                                         response=categorization,
                                         index=i + 1,
                                         category=route_category)

                    if categorization.lower() == route_category.lower():
                        has_match = True
                        logger.info(i18n.t('components.logic.llm_conditional_router.logs.default_check_match_found',
                                           index=i + 1,
                                           response=categorization))
                        self.status = i18n.t('components.logic.llm_conditional_router.status.default_check_match_found',
                                             index=i + 1,
                                             response=categorization)
                        break

                if not has_match:
                    available_cats = [category.get(
                        "route_category", "") for category in categories]
                    logger.info(i18n.t('components.logic.llm_conditional_router.logs.default_check_no_match',
                                       response=categorization,
                                       categories=available_cats))
                    self.status = i18n.t('components.logic.llm_conditional_router.status.default_check_no_match',
                                         response=categorization,
                                         categories=available_cats)

            except RuntimeError:
                logger.debug(i18n.t('components.logic.llm_conditional_router.logs.default_check_error'),
                             exc_info=True)
                pass  # If there's an error, treat as no match

        if has_match:
            # A case matches, stop this output
            logger.debug(
                i18n.t('components.logic.llm_conditional_router.logs.stopping_default_output'))
            self.stop("default_result")
            return Message(text="")

        # No case matches, check for override output first, then use input as default
        override_output = getattr(self, "message", None)
        if (
            override_output
            and hasattr(override_output, "text")
            and override_output.text
            and str(override_output.text).strip()
        ):
            status_msg = i18n.t(
                'components.logic.llm_conditional_router.status.else_using_override')
            logger.info(status_msg)
            self.status = status_msg
            return Message(text=str(override_output.text))
        if override_output and isinstance(override_output, str) and override_output.strip():
            status_msg = i18n.t(
                'components.logic.llm_conditional_router.status.else_using_override')
            logger.info(status_msg)
            self.status = status_msg
            return Message(text=str(override_output))

        status_msg = i18n.t(
            'components.logic.llm_conditional_router.status.else_using_input')
        logger.info(status_msg)
        self.status = status_msg
        return Message(text=input_text)
