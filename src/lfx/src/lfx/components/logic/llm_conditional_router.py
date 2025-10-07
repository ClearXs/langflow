from typing import Any
import i18n

from langflow.custom import Component
from langflow.io import BoolInput, HandleInput, MessageInput, MessageTextInput, MultilineInput, Output, TableInput
from langflow.schema.message import Message


class SmartRouterComponent(Component):
    display_name = i18n.t(
        'components.logic.llm_conditional_router.display_name')
    description = i18n.t('components.logic.llm_conditional_router.description')
    documentation: str = "https://docs.langflow.org/components-logic#smart-router"
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
            name="routes",
            display_name=i18n.t(
                'components.logic.llm_conditional_router.routes.display_name'),
            info=i18n.t('components.logic.llm_conditional_router.routes.info'),
            table_schema=[
                {
                    "name": "route_category",
                    "display_name": i18n.t('components.logic.llm_conditional_router.table_schema.route_category.display_name'),
                    "type": "str",
                    "description": i18n.t('components.logic.llm_conditional_router.table_schema.route_category.description'),
                },
                {
                    "name": "output_value",
                    "display_name": i18n.t('components.logic.llm_conditional_router.table_schema.output_value.display_name'),
                    "type": "str",
                    "description": i18n.t('components.logic.llm_conditional_router.table_schema.output_value.description'),
                    "default": "",
                },
            ],
            value=[
                {
                    "route_category": i18n.t('components.logic.llm_conditional_router.default_routes.positive'),
                    "output_value": ""
                },
                {
                    "route_category": i18n.t('components.logic.llm_conditional_router.default_routes.negative'),
                    "output_value": ""
                },
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
        try:
            if field_name in {"routes", "enable_else_output"}:
                frontend_node["outputs"] = []

                # Get the routes data - either from field_value (if routes field) or from component state
                routes_data = field_value if field_name == "routes" else getattr(
                    self, "routes", [])

                # Add a dynamic output for each category - all using the same method
                for i, row in enumerate(routes_data):
                    route_category = row.get("route_category", i18n.t(
                        'components.logic.llm_conditional_router.default_category', number=i + 1))
                    frontend_node["outputs"].append(
                        Output(
                            display_name=route_category,
                            name=f"category_{i + 1}_result",
                            method="process_case",
                            group_outputs=True,
                        )
                    )
                # Add default output only if enabled
                if field_name == "enable_else_output":
                    enable_else = field_value
                else:
                    enable_else = getattr(self, "enable_else_output", False)

                if enable_else:
                    frontend_node["outputs"].append(
                        Output(
                            display_name=i18n.t(
                                'components.logic.llm_conditional_router.outputs.else.display_name'),
                            name="default_result",
                            method="default_response",
                            group_outputs=True
                        )
                    )
            return frontend_node

        except Exception as e:
            error_msg = i18n.t(
                'components.logic.llm_conditional_router.errors.output_update_failed', error=str(e))
            self.log(error_msg, "error")
            return frontend_node

    def process_case(self) -> Message:
        """Process all categories using LLM categorization and return message for matching category."""
        try:
            # Clear any previous match state
            self._matched_category = None

            categories = getattr(self, "routes", [])
            input_text = getattr(self, "input_text", "")

            # Validate inputs
            if not categories:
                error_msg = i18n.t(
                    'components.logic.llm_conditional_router.errors.no_routes_defined')
                self.status = error_msg
                return Message(text="")

            if not input_text.strip():
                warning_msg = i18n.t(
                    'components.logic.llm_conditional_router.warnings.empty_input_text')
                self.status = warning_msg
                return Message(text="")

            # Find the matching category using LLM-based categorization
            matched_category = None
            llm = getattr(self, "llm", None)

            if not llm:
                error_msg = i18n.t(
                    'components.logic.llm_conditional_router.errors.no_llm_provided')
                self.status = error_msg
                return Message(text="")

            # Create prompt for categorization
            category_values = [
                category.get("route_category", i18n.t(
                    'components.logic.llm_conditional_router.default_category', number=i + 1))
                for i, category in enumerate(categories)
            ]
            categories_text = ", ".join(
                [f'"{cat}"' for cat in category_values if cat])

            # Create base prompt
            base_prompt = i18n.t('components.logic.llm_conditional_router.prompts.base_classification',
                                 input_text=input_text, categories=categories_text)

            # Use custom prompt as additional instructions if provided
            custom_prompt = getattr(self, "custom_prompt", "")
            if custom_prompt and custom_prompt.strip():
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.using_custom_prompt')
                # Format custom prompt with variables
                try:
                    formatted_custom = custom_prompt.format(
                        input_text=input_text, routes=categories_text)
                    # Combine base prompt with custom instructions
                    prompt = i18n.t('components.logic.llm_conditional_router.prompts.with_custom_instructions',
                                    base_prompt=base_prompt, custom_instructions=formatted_custom)
                except Exception as e:
                    warning_msg = i18n.t('components.logic.llm_conditional_router.warnings.custom_prompt_format_failed',
                                         error=str(e))
                    self.log(warning_msg, "warning")
                    prompt = base_prompt
            else:
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.using_default_prompt')
                prompt = base_prompt

            # Log the final prompt being sent to LLM
            self.log(i18n.t(
                'components.logic.llm_conditional_router.logs.prompt_sent', prompt=prompt))

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
                self.log(i18n.t(
                    'components.logic.llm_conditional_router.logs.llm_response', response=categorization))

                # Find matching category based on LLM response
                for i, category in enumerate(categories):
                    route_category = category.get("route_category", "")

                    # Log each comparison attempt
                    self.log(i18n.t('components.logic.llm_conditional_router.logs.comparing_categories',
                                    response=categorization, index=i + 1, category=route_category))

                    if categorization.lower() == route_category.lower():
                        matched_category = i
                        self.log(i18n.t('components.logic.llm_conditional_router.logs.match_found',
                                        index=i + 1, response=categorization))
                        break

                if matched_category is None:
                    available_categories = [category.get(
                        'route_category', '') for category in categories]
                    self.log(i18n.t('components.logic.llm_conditional_router.logs.no_match_found',
                                    response=categorization, available=str(available_categories)))

            except Exception as e:
                error_msg = i18n.t(
                    'components.logic.llm_conditional_router.errors.llm_categorization_failed', error=str(e))
                self.status = error_msg
                self.log(error_msg, "error")
                return Message(text="")

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

                route_category = categories[matched_category].get("route_category",
                                                                  i18n.t('components.logic.llm_conditional_router.default_category', number=matched_category + 1))
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.categorized_as', category=route_category)

                # Check if there's an override output (takes precedence over everything)
                override_output = getattr(self, "message", None)
                if (
                    override_output
                    and hasattr(override_output, "text")
                    and override_output.text
                    and str(override_output.text).strip()
                ):
                    return Message(text=str(override_output.text))
                if override_output and isinstance(override_output, str) and override_output.strip():
                    return Message(text=str(override_output))

                # Check if there's a custom output value for this category
                custom_output = categories[matched_category].get(
                    "output_value", "")
                # Treat None, empty string, or whitespace as blank
                if custom_output and str(custom_output).strip() and str(custom_output).strip().lower() != "none":
                    # Use custom output value
                    return Message(text=str(custom_output))
                # Use input as default output
                return Message(text=input_text)

            # No match found, stop all category outputs
            for i in range(len(categories)):
                self.stop(f"category_{i + 1}_result")

            # Check if else output is enabled
            enable_else = getattr(self, "enable_else_output", False)
            if enable_else:
                # The default_response will handle the else case
                self.stop("process_case")
                return Message(text="")
            # No else output, so no output at all
            self.status = i18n.t(
                'components.logic.llm_conditional_router.status.no_match_no_else')
            return Message(text="")

        except Exception as e:
            error_msg = i18n.t(
                'components.logic.llm_conditional_router.errors.process_case_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            return Message(text="")

    def default_response(self) -> Message:
        """Handle the else case when no conditions match."""
        try:
            # Check if else output is enabled
            enable_else = getattr(self, "enable_else_output", False)
            if not enable_else:
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.else_output_disabled')
                return Message(text="")

            # Clear any previous match state if not already set
            if not hasattr(self, "_matched_category"):
                self._matched_category = None

            categories = getattr(self, "routes", [])
            input_text = getattr(self, "input_text", "")

            # Check if a match was already found in process_case
            if hasattr(self, "_matched_category") and self._matched_category is not None:
                self.status = i18n.t('components.logic.llm_conditional_router.status.match_already_found',
                                     category=self._matched_category + 1)
                self.stop("default_result")
                return Message(text="")

            # Check if any category matches using LLM categorization
            has_match = False
            llm = getattr(self, "llm", None)

            if llm and categories:
                try:
                    # Create prompt for categorization
                    category_values = [
                        category.get("route_category", i18n.t(
                            'components.logic.llm_conditional_router.default_category', number=i + 1))
                        for i, category in enumerate(categories)
                    ]
                    categories_text = ", ".join(
                        [f'"{cat}"' for cat in category_values if cat])

                    # Create base prompt
                    base_prompt = i18n.t('components.logic.llm_conditional_router.prompts.base_classification',
                                         input_text=input_text, categories=categories_text)

                    # Use custom prompt as additional instructions if provided
                    custom_prompt = getattr(self, "custom_prompt", "")
                    if custom_prompt and custom_prompt.strip():
                        self.status = i18n.t(
                            'components.logic.llm_conditional_router.status.using_custom_prompt_default_check')
                        # Format custom prompt with variables
                        try:
                            formatted_custom = custom_prompt.format(
                                input_text=input_text, routes=categories_text)
                            # Combine base prompt with custom instructions
                            prompt = i18n.t('components.logic.llm_conditional_router.prompts.with_custom_instructions',
                                            base_prompt=base_prompt, custom_instructions=formatted_custom)
                        except Exception as e:
                            warning_msg = i18n.t('components.logic.llm_conditional_router.warnings.custom_prompt_format_failed',
                                                 error=str(e))
                            self.log(warning_msg, "warning")
                            prompt = base_prompt
                    else:
                        self.status = i18n.t(
                            'components.logic.llm_conditional_router.status.using_default_prompt_default_check')
                        prompt = base_prompt

                    # Log the final prompt being sent to LLM for default check
                    self.log(i18n.t(
                        'components.logic.llm_conditional_router.logs.default_check_prompt_sent', prompt=prompt))

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
                    self.log(i18n.t('components.logic.llm_conditional_router.logs.default_check_llm_response',
                                    response=categorization))

                    # Check if LLM response matches any category
                    for i, category in enumerate(categories):
                        route_category = category.get("route_category", "")

                        # Log each comparison attempt
                        self.log(i18n.t('components.logic.llm_conditional_router.logs.default_check_comparing',
                                        response=categorization, index=i + 1, category=route_category))

                        if categorization.lower() == route_category.lower():
                            has_match = True
                            self.log(i18n.t('components.logic.llm_conditional_router.logs.default_check_match_found',
                                            index=i + 1, response=categorization))
                            break

                    if not has_match:
                        available_categories = [category.get(
                            'route_category', '') for category in categories]
                        self.log(i18n.t('components.logic.llm_conditional_router.logs.default_check_no_match',
                                        response=categorization, available=str(available_categories)))

                except Exception as e:
                    warning_msg = i18n.t(
                        'components.logic.llm_conditional_router.warnings.default_check_failed', error=str(e))
                    self.log(warning_msg, "warning")
                    # If there's an error, treat as no match

            if has_match:
                # A case matches, stop this output
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
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.else_using_override')
                return Message(text=str(override_output.text))
            if override_output and isinstance(override_output, str) and override_output.strip():
                self.status = i18n.t(
                    'components.logic.llm_conditional_router.status.else_using_override')
                return Message(text=str(override_output))

            self.status = i18n.t(
                'components.logic.llm_conditional_router.status.else_using_input_default')
            return Message(text=input_text)

        except Exception as e:
            error_msg = i18n.t(
                'components.logic.llm_conditional_router.errors.default_response_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            return Message(text="")
