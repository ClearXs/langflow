import json
import os
import string
from typing import Any, cast

import i18n
from apify_client import ApifyClient
from langchain_community.document_loaders.apify_dataset import ApifyDatasetLoader
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, field_serializer

from lfx.custom.custom_component.component import Component
from lfx.field_typing import Tool
from lfx.inputs.inputs import BoolInput
from lfx.io import MultilineInput, Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data

MAX_DESCRIPTION_LEN = 250


class ApifyActorsComponent(Component):
    display_name = i18n.t('components.apify.apify_actor.display_name')
    description = i18n.t('components.apify.apify_actor.description')
    documentation: str = "http://docs.langflow.org/integrations-apify"
    icon = "Apify"
    name = "ApifyActors"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="apify_token",
            display_name=i18n.t(
                'components.apify.apify_actor.apify_token.display_name'),
            info=i18n.t('components.apify.apify_actor.apify_token.info'),
            required=True,
            password=True,
        ),
        StrInput(
            name="actor_id",
            display_name=i18n.t(
                'components.apify.apify_actor.actor_id.display_name'),
            info=i18n.t('components.apify.apify_actor.actor_id.info'),
            value="apify/website-content-crawler",
            required=True,
        ),
        MultilineInput(
            name="run_input",
            display_name=i18n.t(
                'components.apify.apify_actor.run_input.display_name'),
            info=i18n.t('components.apify.apify_actor.run_input.info'),
            value='{"startUrls":[{"url":"https://docs.apify.com/academy/web-scraping-for-beginners"}],"maxCrawlDepth":0}',
            required=True,
        ),
        MultilineInput(
            name="dataset_fields",
            display_name=i18n.t(
                'components.apify.apify_actor.dataset_fields.display_name'),
            info=i18n.t('components.apify.apify_actor.dataset_fields.info'),
        ),
        BoolInput(
            name="flatten_dataset",
            display_name=i18n.t(
                'components.apify.apify_actor.flatten_dataset.display_name'),
            info=i18n.t('components.apify.apify_actor.flatten_dataset.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.apify.apify_actor.outputs.output.display_name'),
            name="output",
            type_=list[Data],
            method="run_model"
        ),
        Output(
            display_name=i18n.t(
                'components.apify.apify_actor.outputs.tool.display_name'),
            name="tool",
            type_=Tool,
            method="build_tool"
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._apify_client: ApifyClient | None = None

    def run_model(self) -> list[Data]:
        """Run the Actor and return node output."""
        try:
            self.status = i18n.t(
                'components.apify.apify_actor.status.parsing_input')

            try:
                input_ = json.loads(self.run_input)
            except json.JSONDecodeError as e:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.invalid_json', error=str(e))
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            fields = ApifyActorsComponent.parse_dataset_fields(
                self.dataset_fields) if self.dataset_fields else None

            logger.info(i18n.t('components.apify.apify_actor.logs.running_actor',
                               actor=self.actor_id, fields=len(fields) if fields else 0))

            res = self._run_actor(self.actor_id, input_, fields=fields)

            if self.flatten_dataset:
                self.status = i18n.t(
                    'components.apify.apify_actor.status.flattening_dataset')
                res = [ApifyActorsComponent.flatten(item) for item in res]
                logger.debug(
                    i18n.t('components.apify.apify_actor.logs.dataset_flattened'))

            data = [Data(data=item) for item in res]

            success_msg = i18n.t('components.apify.apify_actor.success.actor_run_completed',
                                 count=len(data))
            logger.info(success_msg)
            self.status = success_msg

            return data

        except (ValueError, json.JSONDecodeError):
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.apify.apify_actor.errors.run_model_failed', error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    def build_tool(self) -> Tool:
        """Build a tool for an agent that runs the Apify Actor."""
        try:
            self.status = i18n.t(
                'components.apify.apify_actor.status.building_tool')

            actor_id = self.actor_id

            logger.debug(
                i18n.t('components.apify.apify_actor.logs.fetching_build', actor=actor_id))
            build = self._get_actor_latest_build(actor_id)

            readme = build.get("readme", "")[:250] + "..."
            if not (input_schema_str := build.get("inputSchema")):
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.input_schema_not_found')
                raise ValueError(error_msg)

            input_schema = json.loads(input_schema_str)
            properties, required = ApifyActorsComponent.get_actor_input_schema_from_build(
                input_schema)
            properties = {"run_input": properties}

            info_ = [
                i18n.t('components.apify.apify_actor.tool.input_schema_prefix'),
                f"\n\n{json.dumps(properties, separators=(',', ':'))}"
            ]
            if required:
                info_.append(
                    i18n.t('components.apify.apify_actor.tool.required_fields_prefix') +
                    "\n" + "\n".join(required)
                )

            info = "".join(info_)

            input_model_cls = ApifyActorsComponent.create_input_model_class(
                info)
            tool_cls = ApifyActorsComponent.create_tool_class(
                self, readme, input_model_cls, actor_id)

            success_msg = i18n.t(
                'components.apify.apify_actor.success.tool_built', actor=actor_id)
            logger.info(success_msg)
            self.status = success_msg

            return cast("Tool", tool_cls())

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.apify.apify_actor.errors.build_tool_failed', error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    @staticmethod
    def create_tool_class(
        parent: "ApifyActorsComponent", readme: str, input_model: type[BaseModel], actor_id: str
    ) -> type[BaseTool]:
        """Create a tool class that runs an Apify Actor."""

        class ApifyActorRun(BaseTool):
            """Tool that runs Apify Actors."""

            name: str = f"apify_actor_{ApifyActorsComponent.actor_id_to_tool_name(actor_id)}"
            description: str = (
                i18n.t('components.apify.apify_actor.tool.description_prefix') +
                f"\n\n{readme}\n\n"
            )

            args_schema: type[BaseModel] = input_model

            @field_serializer("args_schema")
            def serialize_args_schema(self, args_schema):
                return args_schema.schema()

            def _run(self, run_input: str | dict) -> str:
                """Use the Apify Actor."""
                try:
                    input_dict = json.loads(run_input) if isinstance(
                        run_input, str) else run_input
                    input_dict = input_dict.get("run_input", input_dict)

                    res = parent._run_actor(actor_id, input_dict)
                    return "\n\n".join([ApifyActorsComponent.dict_to_json_str(item) for item in res])

                except Exception as e:
                    error_msg = i18n.t(
                        'components.apify.apify_actor.errors.tool_run_failed', error=str(e))
                    logger.exception(error_msg)
                    raise ValueError(error_msg) from e

        return ApifyActorRun

    @staticmethod
    def create_input_model_class(description: str) -> type[BaseModel]:
        """Create a Pydantic model class for the Actor input."""

        class ActorInput(BaseModel):
            """Input for the Apify Actor tool."""

            run_input: str = Field(..., description=description)

        return ActorInput

    def _get_apify_client(self) -> ApifyClient:
        """Get the Apify client."""
        try:
            if not self.apify_token:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.api_token_required')
                raise ValueError(error_msg)

            if self._apify_client is None or self._apify_client.token != self.apify_token:
                self._apify_client = ApifyClient(self.apify_token)
                if httpx_client := self._apify_client.http_client.httpx_client:
                    httpx_client.headers["user-agent"] += "; Origin/langflow"
                logger.debug(
                    i18n.t('components.apify.apify_actor.logs.client_created'))

            return self._apify_client

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.apify.apify_actor.errors.client_creation_failed', error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    def _get_actor_latest_build(self, actor_id: str) -> dict:
        """Get the latest build of an Actor from the default build tag."""
        try:
            client = self._get_apify_client()
            actor = client.actor(actor_id=actor_id)

            if not (actor_info := actor.get()):
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.actor_not_found', actor=actor_id)
                raise ValueError(error_msg)

            default_build_tag = actor_info.get(
                "defaultRunOptions", {}).get("build")
            latest_build_id = actor_info.get("taggedBuilds", {}).get(
                default_build_tag, {}).get("buildId")

            if (build := client.build(latest_build_id).get()) is None:
                error_msg = i18n.t('components.apify.apify_actor.errors.build_not_found',
                                   build=latest_build_id)
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.apify.apify_actor.logs.build_retrieved',
                                actor=actor_id, build=latest_build_id))
            return build

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.apify.apify_actor.errors.get_build_failed',
                               actor=actor_id, error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    @staticmethod
    def get_actor_input_schema_from_build(input_schema: dict) -> tuple[dict, list[str]]:
        """Get the input schema from the Actor build."""
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        properties_out: dict = {}
        for item, meta in properties.items():
            properties_out[item] = {}
            if desc := meta.get("description"):
                properties_out[item]["description"] = (
                    desc[:MAX_DESCRIPTION_LEN] +
                    "..." if len(desc) > MAX_DESCRIPTION_LEN else desc
                )
            for key_name in ("type", "default", "prefill", "enum"):
                if value := meta.get(key_name):
                    properties_out[item][key_name] = value

        return properties_out, required

    def _get_run_dataset_id(self, run_id: str) -> str:
        """Get the dataset id from the run id."""
        try:
            client = self._get_apify_client()
            run = client.run(run_id=run_id)

            if (dataset := run.dataset().get()) is None:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.dataset_not_found')
                raise ValueError(error_msg)

            if (did := dataset.get("id")) is None:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.dataset_id_not_found')
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.apify.apify_actor.logs.dataset_id_retrieved',
                                run=run_id, dataset=did))
            return did

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.apify.apify_actor.errors.get_dataset_id_failed',
                               run=run_id, error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    @staticmethod
    def dict_to_json_str(d: dict) -> str:
        """Convert a dictionary to a JSON string."""
        return json.dumps(d, separators=(",", ":"), default=lambda _: "<n/a>")

    @staticmethod
    def actor_id_to_tool_name(actor_id: str) -> str:
        """Turn actor_id into a valid tool name."""
        valid_chars = string.ascii_letters + string.digits + "_-"
        return "".join(char if char in valid_chars else "_" for char in actor_id)

    def _run_actor(self, actor_id: str, run_input: dict, fields: list[str] | None = None) -> list[dict]:
        """Run an Apify Actor and return the output dataset."""
        try:
            self.status = i18n.t(
                'components.apify.apify_actor.status.calling_actor', actor=actor_id)

            client = self._get_apify_client()
            if (details := client.actor(actor_id=actor_id).call(run_input=run_input, wait_secs=1)) is None:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.actor_run_details_not_found')
                raise ValueError(error_msg)

            if (run_id := details.get("id")) is None:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.run_id_not_found')
                raise ValueError(error_msg)

            if (run_client := client.run(run_id)) is None:
                error_msg = i18n.t(
                    'components.apify.apify_actor.errors.run_client_not_found')
                raise ValueError(error_msg)

            self.status = i18n.t(
                'components.apify.apify_actor.status.streaming_logs', run=run_id)

            # stream logs
            with run_client.log().stream() as response:
                if response:
                    for line in response.iter_lines():
                        self.log(line)

            self.status = i18n.t(
                'components.apify.apify_actor.status.waiting_for_finish')
            run_client.wait_for_finish()

            logger.info(
                i18n.t('components.apify.apify_actor.logs.actor_run_finished', run=run_id))

            self.status = i18n.t(
                'components.apify.apify_actor.status.loading_dataset')
            dataset_id = self._get_run_dataset_id(run_id)

            loader = ApifyDatasetLoader(
                dataset_id=dataset_id,
                dataset_mapping_function=lambda item: item
                if not fields
                else {k.replace(".", "_"): ApifyActorsComponent.get_nested_value(item, k) for k in fields},
            )

            result = loader.load()
            logger.info(i18n.t('components.apify.apify_actor.logs.dataset_loaded',
                               dataset=dataset_id, items=len(result)))

            return result

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.apify.apify_actor.errors.run_actor_failed',
                               actor=actor_id, error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    @staticmethod
    def get_nested_value(data: dict[str, Any], key: str) -> Any:
        """Get a nested value from a dictionary."""
        keys = key.split(".")
        value = data
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]
        return value

    @staticmethod
    def parse_dataset_fields(dataset_fields: str) -> list[str]:
        """Convert a string of comma-separated fields into a list of fields."""
        dataset_fields = dataset_fields.replace(
            "'", "").replace('"', "").replace("`", "")
        return [field.strip() for field in dataset_fields.split(",")]

    @staticmethod
    def flatten(d: dict) -> dict:
        """Flatten a nested dictionary."""

        def items():
            for key, value in d.items():
                if isinstance(value, dict):
                    for subkey, subvalue in ApifyActorsComponent.flatten(value).items():
                        yield key + "_" + subkey, subvalue
                else:
                    yield key, value

        return dict(items())
