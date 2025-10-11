import os
import i18n
from lfx.base.agents.crewai.tasks import HierarchicalTask
from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, MultilineInput, Output
from lfx.log.logger import logger


class HierarchicalTaskComponent(Component):
    display_name: str = i18n.t(
        'components.crewai.hierarchical_task.display_name')
    description: str = i18n.t(
        'components.crewai.hierarchical_task.description')
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MultilineInput(
            name="task_description",
            display_name=i18n.t(
                'components.crewai.hierarchical_task.task_description.display_name'),
            info=i18n.t(
                'components.crewai.hierarchical_task.task_description.info'),
        ),
        MultilineInput(
            name="expected_output",
            display_name=i18n.t(
                'components.crewai.hierarchical_task.expected_output.display_name'),
            info=i18n.t(
                'components.crewai.hierarchical_task.expected_output.info'),
        ),
        HandleInput(
            name="tools",
            display_name=i18n.t(
                'components.crewai.hierarchical_task.tools.display_name'),
            input_types=["Tool"],
            is_list=True,
            info=i18n.t('components.crewai.hierarchical_task.tools.info'),
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.crewai.hierarchical_task.outputs.task.display_name'),
            name="task_output",
            method="build_task"
        ),
    ]

    def build_task(self) -> HierarchicalTask:
        """Build a hierarchical task for CrewAI.

        Returns:
            HierarchicalTask: Configured hierarchical task instance.

        Raises:
            ValueError: If task creation fails.
        """
        try:
            logger.info(
                i18n.t('components.crewai.hierarchical_task.logs.building_task'))
            self.status = i18n.t(
                'components.crewai.hierarchical_task.status.building')

            logger.debug(i18n.t('components.crewai.hierarchical_task.logs.task_details',
                                description_length=len(
                                    self.task_description) if self.task_description else 0,
                                tool_count=len(self.tools) if self.tools else 0))

            task = HierarchicalTask(
                description=self.task_description,
                expected_output=self.expected_output,
                tools=self.tools or [],
            )

            success_msg = i18n.t(
                'components.crewai.hierarchical_task.status.task_created')
            self.status = task
            logger.info(success_msg)

            return task

        except Exception as e:
            error_msg = i18n.t('components.crewai.hierarchical_task.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
