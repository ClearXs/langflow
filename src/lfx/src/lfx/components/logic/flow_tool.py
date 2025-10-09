from typing import Any

import i18n
from typing_extensions import override

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.base.tools.flow_tool import FlowTool
from lfx.field_typing import Tool
from lfx.graph.graph.base import Graph
from lfx.helpers import get_flow_inputs
from lfx.io import BoolInput, DropdownInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict


class FlowToolComponent(LCToolComponent):
    display_name = i18n.t('components.logic.flow_tool.display_name')
    description = i18n.t('components.logic.flow_tool.description')
    field_order = ["flow_name", "name", "description", "return_direct"]
    trace_type = "tool"
    name = "FlowTool"
    legacy: bool = True
    replacement = ["logic.RunFlow"]
    icon = "hammer"

    async def get_flow_names(self) -> list[str]:
        logger.debug(
            i18n.t('components.logic.flow_tool.logs.fetching_flow_names'))
        flow_datas = await self.alist_flows()
        flow_names = [flow_data.data["name"] for flow_data in flow_datas]
        logger.info(i18n.t('components.logic.flow_tool.logs.flow_names_fetched',
                           count=len(flow_names)))
        return flow_names

    async def get_flow(self, flow_name: str) -> Data | None:
        """Retrieves a flow by its name.

        Args:
            flow_name (str): The name of the flow to retrieve.

        Returns:
            Optional[Text]: The flow record if found, None otherwise.
        """
        logger.debug(i18n.t('components.logic.flow_tool.logs.searching_flow',
                            flow_name=flow_name))

        flow_datas = await self.alist_flows()
        for flow_data in flow_datas:
            if flow_data.data["name"] == flow_name:
                logger.info(i18n.t('components.logic.flow_tool.logs.flow_found',
                                   flow_name=flow_name))
                return flow_data

        logger.warning(i18n.t('components.logic.flow_tool.logs.flow_not_found',
                              flow_name=flow_name))
        return None

    @override
    async def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name == "flow_name":
            logger.debug(
                i18n.t('components.logic.flow_tool.logs.updating_flow_list'))
            build_config["flow_name"]["options"] = await self.get_flow_names()

        return build_config

    inputs = [
        DropdownInput(
            name="flow_name",
            display_name=i18n.t(
                'components.logic.flow_tool.flow_name.display_name'),
            info=i18n.t('components.logic.flow_tool.flow_name.info'),
            refresh_button=True
        ),
        StrInput(
            name="tool_name",
            display_name=i18n.t(
                'components.logic.flow_tool.tool_name.display_name'),
            info=i18n.t('components.logic.flow_tool.tool_name.info'),
        ),
        StrInput(
            name="tool_description",
            display_name=i18n.t(
                'components.logic.flow_tool.tool_description.display_name'),
            info=i18n.t('components.logic.flow_tool.tool_description.info'),
        ),
        BoolInput(
            name="return_direct",
            display_name=i18n.t(
                'components.logic.flow_tool.return_direct.display_name'),
            info=i18n.t('components.logic.flow_tool.return_direct.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="api_build_tool",
            display_name=i18n.t(
                'components.logic.flow_tool.outputs.tool.display_name'),
            method="build_tool"
        ),
    ]

    async def build_tool(self) -> Tool:
        try:
            FlowTool.model_rebuild()

            # Validate flow_name
            if "flow_name" not in self._attributes or not self._attributes["flow_name"]:
                error_msg = i18n.t(
                    'components.logic.flow_tool.errors.flow_name_required')
                logger.error(error_msg)
                raise ValueError(error_msg)

            flow_name = self._attributes["flow_name"]

            # Get flow
            self.status = i18n.t('components.logic.flow_tool.status.loading_flow',
                                 flow_name=flow_name)
            logger.info(i18n.t('components.logic.flow_tool.logs.loading_flow',
                               flow_name=flow_name))

            flow_data = await self.get_flow(flow_name)
            if not flow_data:
                error_msg = i18n.t('components.logic.flow_tool.errors.flow_not_found',
                                   flow_name=flow_name)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Build graph
            self.status = i18n.t(
                'components.logic.flow_tool.status.building_graph')
            logger.debug(
                i18n.t('components.logic.flow_tool.logs.building_graph'))

            graph = Graph.from_payload(
                flow_data.data["data"],
                user_id=str(self.user_id),
            )

            # Set run_id
            try:
                graph.set_run_id(self.graph.run_id)
                logger.debug(i18n.t('components.logic.flow_tool.logs.run_id_set',
                                    run_id=self.graph.run_id))
            except Exception:  # noqa: BLE001
                logger.warning(i18n.t('components.logic.flow_tool.warnings.run_id_failed'),
                               exc_info=True)

            # Get inputs and build tool
            self.status = i18n.t(
                'components.logic.flow_tool.status.building_tool')
            logger.debug(
                i18n.t('components.logic.flow_tool.logs.getting_inputs'))

            inputs = get_flow_inputs(graph)
            tool_description = self.tool_description.strip() or flow_data.description

            logger.info(i18n.t('components.logic.flow_tool.logs.creating_tool',
                               name=self.tool_name,
                               input_count=len(inputs)))

            tool = FlowTool(
                name=self.tool_name,
                description=tool_description,
                graph=graph,
                return_direct=self.return_direct,
                inputs=inputs,
                flow_id=str(flow_data.id),
                user_id=str(self.user_id),
                session_id=self.graph.session_id if hasattr(
                    self, "graph") else None,
            )

            # Build status message
            description_repr = repr(tool.description).strip("'")
            args_str = "\n".join(
                [f"- {arg_name}: {arg_data['description']}"
                 for arg_name, arg_data in tool.args.items()]
            )

            success_msg = i18n.t('components.logic.flow_tool.status.tool_created',
                                 description=description_repr,
                                 args=args_str)
            self.status = success_msg
            logger.info(i18n.t('components.logic.flow_tool.logs.tool_created',
                               name=self.tool_name,
                               flow_name=flow_name))

            return tool

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.logic.flow_tool.errors.tool_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
