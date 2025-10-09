import i18n
from lfx.base.agents.crewai.tasks import SequentialTask
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, HandleInput, MultilineInput, Output
from lfx.log.logger import logger


class SequentialTaskComponent(Component):
    display_name: str = i18n.t(
        'components.crewai.sequential_task.display_name')
    description: str = i18n.t('components.crewai.sequential_task.description')
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    inputs = [
        MultilineInput(
            name="task_description",
            display_name=i18n.t(
                'components.crewai.sequential_task.task_description.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task.task_description.info'),
        ),
        MultilineInput(
            name="expected_output",
            display_name=i18n.t(
                'components.crewai.sequential_task.expected_output.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task.expected_output.info'),
        ),
        HandleInput(
            name="tools",
            display_name=i18n.t(
                'components.crewai.sequential_task.tools.display_name'),
            input_types=["Tool"],
            is_list=True,
            info=i18n.t('components.crewai.sequential_task.tools.info'),
            required=False,
            advanced=True,
        ),
        HandleInput(
            name="agent",
            display_name=i18n.t(
                'components.crewai.sequential_task.agent.display_name'),
            input_types=["Agent"],
            info=i18n.t('components.crewai.sequential_task.agent.info'),
            required=True,
        ),
        HandleInput(
            name="task",
            display_name=i18n.t(
                'components.crewai.sequential_task.task.display_name'),
            input_types=["SequentialTask"],
            info=i18n.t('components.crewai.sequential_task.task.info'),
        ),
        BoolInput(
            name="async_execution",
            display_name=i18n.t(
                'components.crewai.sequential_task.async_execution.display_name'),
            value=True,
            advanced=True,
            info=i18n.t(
                'components.crewai.sequential_task.async_execution.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.crewai.sequential_task.outputs.task.display_name'),
            name="task_output",
            method="build_task"
        ),
    ]

    def build_task(self) -> list[SequentialTask]:
        """Build a sequential task with optional task chaining.

        Returns:
            list[SequentialTask]: List of sequential tasks including previous tasks if chained.
        """
        try:
            logger.info(
                i18n.t('components.crewai.sequential_task.logs.building_task'))
            self.status = i18n.t(
                'components.crewai.sequential_task.status.building')

            tasks: list[SequentialTask] = []

            logger.debug(
                i18n.t('components.crewai.sequential_task.logs.creating_task'))

            task = SequentialTask(
                description=self.task_description,
                expected_output=self.expected_output,
                tools=self.agent.tools,
                async_execution=False,
                agent=self.agent,
            )

            tasks.append(task)
            logger.info(
                i18n.t('components.crewai.sequential_task.logs.task_created'))

            self.status = task

            # Chain with previous task if provided
            if self.task:
                logger.debug(
                    i18n.t('components.crewai.sequential_task.logs.chaining_tasks'))

                if isinstance(self.task, list) and all(isinstance(task_item, SequentialTask) for task_item in self.task):
                    tasks = self.task + tasks
                    logger.info(i18n.t('components.crewai.sequential_task.logs.chained_with_list',
                                       count=len(self.task)))
                elif isinstance(self.task, SequentialTask):
                    tasks = [self.task, *tasks]
                    logger.info(
                        i18n.t('components.crewai.sequential_task.logs.chained_with_single'))
            else:
                logger.debug(
                    i18n.t('components.crewai.sequential_task.logs.single_task'))

            success_msg = i18n.t('components.crewai.sequential_task.status.task_created',
                                 total_count=len(tasks))
            logger.info(success_msg)

            return tasks

        except Exception as e:
            error_msg = i18n.t('components.crewai.sequential_task.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
