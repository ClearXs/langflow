from typing import Any
import i18n

from lfx.base.flow_processing.utils import build_data_from_result_data
from lfx.custom.custom_component.component import Component
from lfx.graph.graph.base import Graph
from lfx.graph.vertex.base import Vertex
from lfx.helpers.flow import get_flow_inputs
from lfx.io import DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict


class SubFlowComponent(Component):
    display_name = i18n.t('components.logic.sub_flow.display_name')
    description = i18n.t('components.logic.sub_flow.description')
    name = "SubFlow"
    legacy: bool = True
    replacement = ["logic.RunFlow"]
    icon = "Workflow"

    async def get_flow_names(self) -> list[str]:
        try:
            flow_data = await self.alist_flows()
            return [flow_data.data["name"] for flow_data in flow_data]
        except Exception as e:
            error_message = i18n.t(
                'components.logic.sub_flow.errors.failed_to_get_flow_names', error=str(e))
            await logger.aexception(error_message)
            return []

    async def get_flow(self, flow_name: str) -> Data | None:
        try:
            flow_datas = await self.alist_flows()
            for flow_data in flow_datas:
                if flow_data.data["name"] == flow_name:
                    return flow_data

            warning_message = i18n.t(
                'components.logic.sub_flow.warnings.flow_not_found', flow=flow_name)
            await logger.awarning(warning_message)
            return None
        except Exception as e:
            error_message = i18n.t(
                'components.logic.sub_flow.errors.failed_to_get_flow', flow=flow_name, error=str(e))
            await logger.aexception(error_message)
            return None

    async def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name == "flow_name":
            try:
                build_config["flow_name"]["options"] = await self.get_flow_names()
            except Exception as e:
                error_message = i18n.t(
                    'components.logic.sub_flow.errors.failed_to_update_flow_options', error=str(e))
                await logger.aexception(error_message)

        # Clean up old build config
        for key in list(build_config.keys()):
            if key not in [x.name for x in self.inputs] + ["code", "_type", "get_final_results_only"]:
                del build_config[key]

        if field_value is not None and field_name == "flow_name":
            try:
                flow_data = await self.get_flow(field_value)
            except Exception as e:
                error_message = i18n.t('components.logic.sub_flow.errors.failed_to_get_flow',
                                       flow=field_value, error=str(e))
                await logger.aexception(error_message)
                self.status = error_message
            else:
                if not flow_data:
                    error_message = i18n.t(
                        'components.logic.sub_flow.errors.flow_not_found', flow=field_value)
                    await logger.aerror(error_message)
                    self.status = error_message
                else:
                    try:
                        graph = Graph.from_payload(flow_data.data["data"])
                        # Get all inputs from the graph
                        inputs = get_flow_inputs(graph)
                        # Add inputs to the build config
                        build_config = self.add_inputs_to_build_config(
                            inputs, build_config)

                        success_message = i18n.t('components.logic.sub_flow.success.build_config_updated',
                                                 flow=field_value, count=len(inputs))
                        self.status = success_message
                    except Exception as e:
                        error_message = i18n.t('components.logic.sub_flow.errors.failed_to_build_graph',
                                               flow=field_value, error=str(e))
                        await logger.aexception(error_message)
                        self.status = error_message

        return build_config

    def add_inputs_to_build_config(self, inputs_vertex: list[Vertex], build_config: dotdict):
        new_fields: list[dotdict] = []

        for vertex in inputs_vertex:
            new_vertex_inputs = []
            field_template = vertex.data["node"]["template"]
            for inp in field_template:
                if inp not in {"code", "_type"}:
                    # Create display name with vertex name prefix
                    original_display_name = field_template[inp].get(
                        "display_name", inp)
                    field_template[inp]["display_name"] = f"{vertex.display_name} - {original_display_name}"
                    field_template[inp]["name"] = vertex.id + "|" + inp
                    new_vertex_inputs.append(field_template[inp])
            new_fields += new_vertex_inputs

        for field in new_fields:
            build_config[field["name"]] = field

        return build_config

    inputs = [
        DropdownInput(
            name="flow_name",
            display_name=i18n.t(
                'components.logic.sub_flow.flow_name.display_name'),
            info=i18n.t('components.logic.sub_flow.flow_name.info'),
            options=[],
            refresh_button=True,
            real_time_refresh=True,
        ),
    ]

    outputs = [
        Output(
            name="flow_outputs",
            display_name=i18n.t(
                'components.logic.sub_flow.outputs.flow_outputs.display_name'),
            method="generate_results"
        )
    ]

    async def generate_results(self) -> list[Data]:
        try:
            tweaks: dict = {}
            tweak_count = 0

            # Process tweaks from attributes
            for field in self._attributes:
                if field != "flow_name" and "|" in field:
                    [node, name] = field.split("|")
                    if node not in tweaks:
                        tweaks[node] = {}
                    tweaks[node][name] = self._attributes[field]
                    tweak_count += 1

            flow_name = self._attributes.get("flow_name")
            if not flow_name:
                error_message = i18n.t(
                    'components.logic.sub_flow.errors.no_flow_selected')
                self.status = error_message
                raise ValueError(error_message)

            if tweak_count > 0:
                info_message = i18n.t('components.logic.sub_flow.info.using_tweaks',
                                      count=tweak_count, flow=flow_name)
                self.status = info_message

            # Execute the sub flow
            executing_message = i18n.t(
                'components.logic.sub_flow.info.executing_sub_flow', flow=flow_name)
            self.status = executing_message

            run_outputs = await self.run_flow(
                tweaks=tweaks,
                flow_name=flow_name,
                output_type="all",
            )

            data: list[Data] = []
            if not run_outputs:
                warning_message = i18n.t(
                    'components.logic.sub_flow.warnings.no_outputs')
                self.status = warning_message
                return data

            run_output = run_outputs[0]
            if run_output is not None:
                for output in run_output.outputs:
                    if output:
                        data.extend(build_data_from_result_data(output))

            success_message = i18n.t('components.logic.sub_flow.success.sub_flow_executed',
                                     flow=flow_name, outputs=len(data))
            self.status = success_message

            return data

        except Exception as e:
            error_message = i18n.t(
                'components.logic.sub_flow.errors.execution_failed', error=str(e))
            self.status = error_message
            await logger.aexception(error_message)
            raise ValueError(error_message) from e
