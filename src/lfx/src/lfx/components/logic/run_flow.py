from typing import Any
import i18n

from lfx.base.tools.run_flow import RunFlowBaseComponent
from lfx.helpers.flow import run_flow
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class RunFlowComponent(RunFlowBaseComponent):
    display_name = i18n.t('components.logic.run_flow.display_name')
    description = i18n.t('components.logic.run_flow.description')
    documentation: str = "https://docs.langflow.org/components-logic#run-flow"
    beta = True
    name = "RunFlow"
    icon = "Workflow"

    inputs = RunFlowBaseComponent.get_base_inputs()
    outputs = RunFlowBaseComponent.get_base_outputs()

    async def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name == "flow_name_selected":
            try:
                build_config["flow_name_selected"]["options"] = await self.get_flow_names()
            except Exception as e:
                error_message = i18n.t(
                    'components.logic.run_flow.errors.failed_to_get_flow_names', error=str(e))
                await logger.aexception(error_message)
                raise RuntimeError(error_message) from e

            missing_keys = [
                key for key in self.default_keys if key not in build_config]
            if missing_keys:
                error_message = i18n.t(
                    'components.logic.run_flow.errors.missing_required_keys', keys=', '.join(missing_keys))
                raise ValueError(error_message)

            if field_value is not None:
                try:
                    graph = await self.get_graph(field_value)
                    build_config = self.update_build_config_from_graph(
                        build_config, graph)
                    success_message = i18n.t(
                        'components.logic.run_flow.success.build_config_updated', flow=field_value)
                    self.status = success_message
                except Exception as e:
                    error_message = i18n.t(
                        'components.logic.run_flow.errors.failed_to_build_graph', flow=field_value, error=str(e))
                    await logger.aexception(error_message)
                    self.status = error_message
                    raise RuntimeError(error_message) from e
        return build_config

    async def run_flow_with_tweaks(self):
        try:
            tweaks: dict = {}

            flow_name_selected = self._attributes.get("flow_name_selected")
            if not flow_name_selected:
                error_message = i18n.t(
                    'components.logic.run_flow.errors.no_flow_selected')
                self.status = error_message
                raise ValueError(error_message)

            parsed_flow_tweak_data = self._attributes.get(
                "flow_tweak_data", {})
            if not isinstance(parsed_flow_tweak_data, dict):
                parsed_flow_tweak_data = parsed_flow_tweak_data.dict()

            # Process tweaks from flow_tweak_data
            if parsed_flow_tweak_data != {}:
                for field in parsed_flow_tweak_data:
                    if "~" in field:
                        [node, name] = field.split("~")
                        if node not in tweaks:
                            tweaks[node] = {}
                        tweaks[node][name] = parsed_flow_tweak_data[field]

                info_message = i18n.t(
                    'components.logic.run_flow.info.using_flow_tweak_data', count=len(parsed_flow_tweak_data))
                self.status = info_message
            else:
                # Process tweaks from attributes
                tweak_count = 0
                for field in self._attributes:
                    if field not in self.default_keys and "~" in field:
                        [node, name] = field.split("~")
                        if node not in tweaks:
                            tweaks[node] = {}
                        tweaks[node][name] = self._attributes[field]
                        tweak_count += 1

                if tweak_count > 0:
                    info_message = i18n.t(
                        'components.logic.run_flow.info.using_attribute_tweaks', count=tweak_count)
                    self.status = info_message

            # Execute the flow
            executing_message = i18n.t(
                'components.logic.run_flow.info.executing_flow', flow=flow_name_selected)
            self.status = executing_message

            result = await run_flow(
                inputs=None,
                output_type="all",
                flow_id=None,
                flow_name=flow_name_selected,
                tweaks=tweaks,
                user_id=str(self.user_id),
                session_id=self.graph.session_id or self.session_id,
            )

            success_message = i18n.t(
                'components.logic.run_flow.success.flow_executed', flow=flow_name_selected)
            self.status = success_message

            return result

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            error_message = i18n.t(
                'components.logic.run_flow.errors.execution_failed', error=str(e))
            self.status = error_message
            await logger.aexception(error_message)
            raise RuntimeError(error_message) from e
