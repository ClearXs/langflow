import asyncio
import http  # Added for HTTPStatus
import json
from typing import Any
import i18n

import aiohttp

from lfx.base.models.chat_result import get_chat_result
from lfx.base.models.model_utils import get_model_name
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, DropdownInput, HandleInput, IntInput, MultilineInput
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.template.field.base import Output


class LLMRouterComponent(Component):
    display_name = i18n.t('components.processing.llm_router.display_name')
    description = i18n.t('components.processing.llm_router.description')
    documentation: str = "https://docs.langflow.org/components-processing#llm-router"
    icon = "git-branch"

    # Constants for magic values
    MAX_DESCRIPTION_LENGTH = 500
    QUERY_PREVIEW_MAX_LENGTH = 1000

    inputs = [
        HandleInput(
            name="models",
            display_name=i18n.t(
                'components.processing.llm_router.models.display_name'),
            input_types=["LanguageModel"],
            required=True,
            is_list=True,
            info=i18n.t('components.processing.llm_router.models.info'),
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.processing.llm_router.input_value.display_name'),
            required=True,
            info=i18n.t('components.processing.llm_router.input_value.info'),
        ),
        HandleInput(
            name="judge_llm",
            display_name=i18n.t(
                'components.processing.llm_router.judge_llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
            info=i18n.t('components.processing.llm_router.judge_llm.info'),
        ),
        DropdownInput(
            name="optimization",
            display_name=i18n.t(
                'components.processing.llm_router.optimization.display_name'),
            options=[
                i18n.t('components.processing.llm_router.optimization.quality'),
                i18n.t('components.processing.llm_router.optimization.speed'),
                i18n.t('components.processing.llm_router.optimization.cost'),
                i18n.t('components.processing.llm_router.optimization.balanced')
            ],
            value=i18n.t(
                'components.processing.llm_router.optimization.balanced'),
            info=i18n.t('components.processing.llm_router.optimization.info'),
        ),
        BoolInput(
            name="use_openrouter_specs",
            display_name=i18n.t(
                'components.processing.llm_router.use_openrouter_specs.display_name'),
            value=True,
            info=i18n.t(
                'components.processing.llm_router.use_openrouter_specs.info'),
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.processing.llm_router.timeout.display_name'),
            value=10,
            info=i18n.t('components.processing.llm_router.timeout.info'),
            advanced=True,
        ),
        BoolInput(
            name="fallback_to_first",
            display_name=i18n.t(
                'components.processing.llm_router.fallback_to_first.display_name'),
            value=True,
            info=i18n.t(
                'components.processing.llm_router.fallback_to_first.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.llm_router.outputs.output.display_name'),
            name="output",
            method="route_to_model"
        ),
        Output(
            display_name=i18n.t(
                'components.processing.llm_router.outputs.selected_model_info.display_name'),
            name="selected_model_info",
            method="get_selected_model_info",
            types=["Data"],
        ),
        Output(
            display_name=i18n.t(
                'components.processing.llm_router.outputs.routing_decision.display_name'),
            name="routing_decision",
            method="get_routing_decision",
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_model_name: str | None = None
        self._selected_api_model_id: str | None = None
        self._routing_decision: str = ""
        self._models_api_cache: dict[str, dict[str, Any]] = {}
        self._model_name_to_api_id: dict[str, str] = {}

    def _simplify_model_name(self, name: str) -> str:
        """Simplify model name for matching by lowercasing and removing non-alphanumerics."""
        return "".join(c.lower() for c in name if c.isalnum())

    async def _fetch_openrouter_models_data(self) -> None:
        """Fetch all models from OpenRouter API and cache them along with name mappings."""
        if self._models_api_cache and self._model_name_to_api_id:
            return

        if not self.use_openrouter_specs:
            self.log(
                i18n.t('components.processing.llm_router.logs.openrouter_specs_disabled'))
            return

        try:
            self.status = i18n.t(
                'components.processing.llm_router.status.fetching_openrouter_specs')
            self.log(
                i18n.t('components.processing.llm_router.logs.fetching_openrouter_models'))

            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session,
                session.get("https://openrouter.ai/api/v1/models") as response,
            ):
                if response.status == http.HTTPStatus.OK:
                    data = await response.json()
                    models_list = data.get("data", [])

                    _models_api_cache_temp = {}
                    _model_name_to_api_id_temp = {}

                    for model_data in models_list:
                        api_model_id = model_data.get("id")
                        if not api_model_id:
                            continue

                        _models_api_cache_temp[api_model_id] = model_data
                        _model_name_to_api_id_temp[api_model_id] = api_model_id

                        api_model_name = model_data.get("name")
                        if api_model_name:
                            _model_name_to_api_id_temp[api_model_name] = api_model_id
                            simplified_api_name = self._simplify_model_name(
                                api_model_name)
                            _model_name_to_api_id_temp[simplified_api_name] = api_model_id

                        hugging_face_id = model_data.get("hugging_face_id")
                        if hugging_face_id:
                            _model_name_to_api_id_temp[hugging_face_id] = api_model_id
                            simplified_hf_id = self._simplify_model_name(
                                hugging_face_id)
                            _model_name_to_api_id_temp[simplified_hf_id] = api_model_id

                        if "/" in api_model_id:
                            try:
                                model_name_part_of_id = api_model_id.split(
                                    "/", 1)[1]
                                if model_name_part_of_id:
                                    _model_name_to_api_id_temp[model_name_part_of_id] = api_model_id
                                    simplified_part_id = self._simplify_model_name(
                                        model_name_part_of_id)
                                    _model_name_to_api_id_temp[simplified_part_id] = api_model_id
                            except IndexError:
                                pass  # Should not happen if '/' is present

                    self._models_api_cache = _models_api_cache_temp
                    self._model_name_to_api_id = _model_name_to_api_id_temp

                    log_msg = i18n.t('components.processing.llm_router.logs.openrouter_models_cached',
                                     count=len(self._models_api_cache))
                    self.log(log_msg)
                else:
                    err_text = await response.text()
                    error_msg = i18n.t('components.processing.llm_router.errors.openrouter_fetch_failed',
                                       status=response.status, error=err_text)
                    self.log(error_msg)
                    self._models_api_cache = {}
                    self._model_name_to_api_id = {}
        except aiohttp.ClientError as e:
            error_msg = i18n.t(
                'components.processing.llm_router.errors.openrouter_client_error', error=str(e))
            self.log(error_msg, "error")
            self._models_api_cache = {}
            self._model_name_to_api_id = {}
        except asyncio.TimeoutError:
            error_msg = i18n.t(
                'components.processing.llm_router.errors.openrouter_timeout')
            self.log(error_msg, "error")
            self._models_api_cache = {}
            self._model_name_to_api_id = {}
        except json.JSONDecodeError as e:
            error_msg = i18n.t(
                'components.processing.llm_router.errors.openrouter_json_error', error=str(e))
            self.log(error_msg, "error")
            self._models_api_cache = {}
            self._model_name_to_api_id = {}
        finally:
            self.status = ""

    def _get_api_model_id_for_langflow_model(self, langflow_model_name: str) -> str | None:
        """Attempt to find the OpenRouter API ID for a given Langflow model name."""
        if not langflow_model_name:
            return None

        potential_names_to_check = [langflow_model_name,
                                    self._simplify_model_name(langflow_model_name)]

        if langflow_model_name.startswith("models/"):
            name_without_prefix = langflow_model_name[len("models/"):]
            potential_names_to_check.append(name_without_prefix)
            potential_names_to_check.append(
                self._simplify_model_name(name_without_prefix))

        elif langflow_model_name.startswith("community_models/"):
            name_without_prefix = langflow_model_name[len(
                "community_models/"):]
            potential_names_to_check.append(name_without_prefix)
            simplified_no_prefix = self._simplify_model_name(
                name_without_prefix)
            potential_names_to_check.append(simplified_no_prefix)

        elif langflow_model_name.startswith("community_models/"):
            name_without_prefix = langflow_model_name[len(
                "community_models/"):]
            potential_names_to_check.append(name_without_prefix)
            simplified_no_prefix_comm = self._simplify_model_name(
                name_without_prefix)
            potential_names_to_check.append(simplified_no_prefix_comm)

        unique_names_to_check = list(dict.fromkeys(potential_names_to_check))

        for name_variant in unique_names_to_check:
            if name_variant in self._model_name_to_api_id:
                return self._model_name_to_api_id[name_variant]

        warning_msg = i18n.t('components.processing.llm_router.warnings.model_mapping_failed',
                             langflow_name=langflow_model_name, variants=str(unique_names_to_check))
        self.log(warning_msg)
        return None

    def _get_model_specs_dict(self, langflow_model_name: str) -> dict[str, Any]:
        """Get a dictionary of relevant model specifications for a given Langflow model name."""
        if not self.use_openrouter_specs or not self._models_api_cache:
            return {
                "id": langflow_model_name,
                "name": langflow_model_name,
                "description": i18n.t('components.processing.llm_router.specs_not_available'),
            }

        api_model_id = self._get_api_model_id_for_langflow_model(
            langflow_model_name)

        if not api_model_id or api_model_id not in self._models_api_cache:
            log_msg = i18n.t('components.processing.llm_router.logs.cached_data_not_found',
                             langflow_name=langflow_model_name, api_id=api_model_id)
            self.log(log_msg)
            return {
                "id": langflow_model_name,
                "name": langflow_model_name,
                "description": i18n.t('components.processing.llm_router.specs_not_in_cache'),
            }

        model_data = self._models_api_cache[api_model_id]
        top_provider_data = model_data.get("top_provider", {})
        architecture_data = model_data.get("architecture", {})
        pricing_data = model_data.get("pricing", {})
        description = model_data.get("description", i18n.t(
            'components.processing.llm_router.no_description_available'))
        truncated_description = (
            description[: self.MAX_DESCRIPTION_LENGTH - 3] + "..."
            if len(description) > self.MAX_DESCRIPTION_LENGTH
            else description
        )

        specs = {
            "id": model_data.get("id"),
            "name": model_data.get("name"),
            "description": truncated_description,
            "context_length": top_provider_data.get("context_length") or model_data.get("context_length"),
            "max_completion_tokens": (
                top_provider_data.get("max_completion_tokens") or model_data.get(
                    "max_completion_tokens")
            ),
            "tokenizer": architecture_data.get("tokenizer"),
            "input_modalities": architecture_data.get("input_modalities", []),
            "output_modalities": architecture_data.get("output_modalities", []),
            "pricing_prompt": pricing_data.get("prompt"),
            "pricing_completion": pricing_data.get("completion"),
            "is_moderated": top_provider_data.get("is_moderated"),
            "supported_parameters": model_data.get("supported_parameters", []),
        }
        return {k: v for k, v in specs.items() if v is not None}

    def _create_system_prompt(self) -> str:
        """Create system prompt for the judge LLM."""
        return i18n.t('components.processing.llm_router.system_prompt')

    async def route_to_model(self) -> Message:
        """Main routing method."""
        if not self.models or not self.input_value or not self.judge_llm:
            error_msg = i18n.t(
                'components.processing.llm_router.errors.missing_required_inputs')
            self.status = error_msg
            self.log(f"Validation Error: {error_msg}", "error")
            raise ValueError(error_msg)

        successful_result: Message | None = None
        try:
            log_msg = i18n.t('components.processing.llm_router.logs.starting_routing',
                             model_count=len(self.models))
            self.log(log_msg)
            self.log(f"Optimization preference: {self.optimization}")
            self.log(f"Input length: {len(self.input_value)} characters")

            if self.use_openrouter_specs and not self._models_api_cache:
                await self._fetch_openrouter_models_data()

            system_prompt_content = self._create_system_prompt()
            system_message = {"role": "system",
                              "content": system_prompt_content}

            self.status = i18n.t(
                'components.processing.llm_router.status.analyzing_models')
            model_specs_for_judge = []
            for i, langflow_model_instance in enumerate(self.models):
                langflow_model_name = get_model_name(langflow_model_instance)
                if not langflow_model_name:
                    warning_msg = i18n.t(
                        'components.processing.llm_router.warnings.unknown_model_name', index=i)
                    self.log(warning_msg, "warning")
                    spec_dict = {
                        "id": f"unknown_model_{i}",
                        "name": i18n.t('components.processing.llm_router.unknown_model_name', index=i),
                        "description": i18n.t('components.processing.llm_router.name_not_determined'),
                    }
                else:
                    spec_dict = self._get_model_specs_dict(langflow_model_name)

                model_specs_for_judge.append(
                    {"index": i, "langflow_name": langflow_model_name, "specs": spec_dict})
                log_msg = i18n.t('components.processing.llm_router.logs.prepared_specs',
                                 index=i, langflow_name=langflow_model_name, spec_name=spec_dict.get('name', 'N/A'))
                self.log(log_msg)

            estimated_tokens = len(self.input_value.split()) * 1.3
            self.log(f"Estimated input tokens: {int(estimated_tokens)}")

            query_preview = self.input_value[: self.QUERY_PREVIEW_MAX_LENGTH]
            if len(self.input_value) > self.QUERY_PREVIEW_MAX_LENGTH:
                query_preview += "..."

            # Map optimization preference to internal value for prompt
            optimization_map = {
                i18n.t('components.processing.llm_router.optimization.quality'): "quality",
                i18n.t('components.processing.llm_router.optimization.speed'): "speed",
                i18n.t('components.processing.llm_router.optimization.cost'): "cost",
                i18n.t('components.processing.llm_router.optimization.balanced'): "balanced",
                # Also support English for backwards compatibility
                "quality": "quality",
                "speed": "speed",
                "cost": "cost",
                "balanced": "balanced",
            }
            internal_optimization = optimization_map.get(
                self.optimization, "balanced")

            user_message_content = i18n.t('components.processing.llm_router.user_prompt',
                                          query=query_preview,
                                          optimization=internal_optimization,
                                          tokens=int(estimated_tokens),
                                          models=json.dumps(model_specs_for_judge, indent=2))

            user_message = {"role": "user", "content": user_message_content}

            self.log(
                i18n.t('components.processing.llm_router.logs.requesting_selection'))
            self.status = i18n.t(
                'components.processing.llm_router.status.judge_analyzing')

            response = await self.judge_llm.ainvoke([system_message, user_message])
            selected_index, chosen_model_instance = self._parse_judge_response(
                response.content.strip())
            self._selected_model_name = get_model_name(chosen_model_instance)
            if self._selected_model_name:
                self._selected_api_model_id = (
                    self._get_api_model_id_for_langflow_model(
                        self._selected_model_name) or self._selected_model_name
                )
            else:
                self._selected_api_model_id = "unknown_model"

            specs_source = (
                i18n.t('components.processing.llm_router.specs_source.openrouter')
                if self.use_openrouter_specs and self._models_api_cache
                else i18n.t('components.processing.llm_router.specs_source.basic')
            )

            self._routing_decision = i18n.t('components.processing.llm_router.routing_decision',
                                            index=selected_index,
                                            langflow_name=self._selected_model_name,
                                            api_id=self._selected_api_model_id,
                                            optimization=self.optimization,
                                            input_length=len(self.input_value),
                                            tokens=int(estimated_tokens),
                                            model_count=len(self.models),
                                            specs_source=specs_source)

            log_msg = i18n.t('components.processing.llm_router.logs.judge_decision',
                             index=selected_index,
                             langflow_name=self._selected_model_name,
                             api_id=self._selected_api_model_id)
            self.log(log_msg)

            self.status = i18n.t(
                'components.processing.llm_router.status.generating_response', model=self._selected_model_name)
            input_message_obj = Message(text=self.input_value)

            raw_result = get_chat_result(
                runnable=chosen_model_instance,
                input_value=input_message_obj,
            )
            result = Message(text=str(raw_result)) if not isinstance(
                raw_result, Message) else raw_result

            self.status = i18n.t(
                'components.processing.llm_router.status.successfully_routed', model=self._selected_model_name)
            successful_result = result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            error_msg = i18n.t('components.processing.llm_router.errors.routing_error',
                               error_type=type(e).__name__, error=str(e))
            self.log(error_msg, "error")
            self.log(
                i18n.t('components.processing.llm_router.logs.detailed_error'), "error")
            self.status = error_msg

            if self.fallback_to_first and self.models:
                self.log(
                    i18n.t('components.processing.llm_router.logs.activating_fallback'), "warning")
                chosen_model_instance = self.models[0]
                self._selected_model_name = get_model_name(
                    chosen_model_instance)
                if self._selected_model_name:
                    mapped_id = self._get_api_model_id_for_langflow_model(
                        self._selected_model_name)
                    self._selected_api_model_id = mapped_id or self._selected_model_name
                else:
                    self._selected_api_model_id = "fallback_model"

                self._routing_decision = i18n.t('components.processing.llm_router.fallback_decision',
                                                error=error_msg,
                                                langflow_name=self._selected_model_name,
                                                api_id=self._selected_api_model_id)

                self.status = i18n.t(
                    'components.processing.llm_router.status.fallback', model=self._selected_model_name)
                input_message_obj = Message(text=self.input_value)

                raw_fallback_result = get_chat_result(
                    runnable=chosen_model_instance,
                    input_value=input_message_obj,
                )
                if not isinstance(raw_fallback_result, Message):
                    successful_result = Message(text=str(raw_fallback_result))
                else:
                    successful_result = raw_fallback_result
            else:
                error_msg = i18n.t(
                    'components.processing.llm_router.errors.no_fallback')
                self.log(error_msg, "error")
                raise

        if successful_result is None:
            error_message = i18n.t(
                'components.processing.llm_router.errors.no_result_produced')
            self.log(f"Error: {error_message}", "error")
            raise RuntimeError(error_message)
        return successful_result

    def _parse_judge_response(self, response_content: str) -> tuple[int, Any]:
        """Parse the judge's response to extract model index."""
        try:
            cleaned_response = "".join(
                filter(str.isdigit, response_content.strip()))
            if not cleaned_response:
                warning_msg = i18n.t('components.processing.llm_router.warnings.non_numeric_response',
                                     response=response_content)
                self.log(warning_msg, "warning")
                return 0, self.models[0]

            selected_index = int(cleaned_response)

            if 0 <= selected_index < len(self.models):
                self.log(i18n.t(
                    'components.processing.llm_router.logs.judge_selected_index', index=selected_index))
                return selected_index, self.models[selected_index]

            warning_msg = i18n.t('components.processing.llm_router.warnings.index_out_of_bounds',
                                 index=selected_index, max_index=len(self.models) - 1)
            self.log(warning_msg, "warning")
            return 0, self.models[0]

        except ValueError:
            warning_msg = i18n.t('components.processing.llm_router.warnings.parse_response_failed',
                                 response=response_content)
            self.log(warning_msg, "warning")
            return 0, self.models[0]
        except (AttributeError, IndexError) as e:
            error_msg = i18n.t('components.processing.llm_router.errors.parse_response_error',
                               response=response_content, error=str(e))
            self.log(error_msg, "error")
            return 0, self.models[0]

    def get_selected_model_info(self) -> list[Data]:
        """Return detailed information about the selected model as a list of Data objects."""
        if self._selected_model_name:
            specs_dict = self._get_model_specs_dict(self._selected_model_name)
            if "langflow_name" not in specs_dict:
                specs_dict["langflow_model_name_used_for_lookup"] = self._selected_model_name
            if self._selected_api_model_id and specs_dict.get("id") != self._selected_api_model_id:
                specs_dict["resolved_api_model_id"] = self._selected_api_model_id
            data_output = [Data(data=specs_dict)]
            self.status = data_output
            return data_output

        no_selection_msg = i18n.t(
            'components.processing.llm_router.no_model_selected')
        data_output = [Data(data={"info": no_selection_msg})]
        self.status = data_output
        return data_output

    def get_routing_decision(self) -> Message:
        """Return the comprehensive routing decision explanation."""
        if self._routing_decision:
            message_output = Message(text=f"{self._routing_decision}")
            self.status = message_output
            return message_output

        no_decision_msg = i18n.t(
            'components.processing.llm_router.no_routing_decision')
        message_output = Message(text=no_decision_msg)
        self.status = message_output
        return message_output
