import os
import i18n
from lfx.base.agents.crewai.crew import BaseCrewComponent
from lfx.io import HandleInput
from lfx.log.logger import logger
from lfx.schema.message import Message


class SequentialCrewComponent(BaseCrewComponent):
    display_name: str = i18n.t(
        'components.crewai.sequential_crew.display_name')
    description: str = i18n.t('components.crewai.sequential_crew.description')
    documentation: str = "https://docs.crewai.com/how-to/Sequential/"
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *BaseCrewComponent.get_base_inputs(),
        HandleInput(
            name="tasks",
            display_name=i18n.t(
                'components.crewai.sequential_crew.tasks.display_name'),
            input_types=["SequentialTask"],
            is_list=True,
            info=i18n.t('components.crewai.sequential_crew.tasks.info')
        ),
    ]

    @property
    def agents(self: "SequentialCrewComponent") -> list:
        """Derive agents directly from linked tasks.

        Returns:
            list: List of agents extracted from sequential tasks.
        """
        logger.debug(
            i18n.t('components.crewai.sequential_crew.logs.deriving_agents'))
        agents = [task.agent for task in self.tasks if hasattr(task, "agent")]
        logger.debug(i18n.t('components.crewai.sequential_crew.logs.agents_derived',
                            count=len(agents)))
        return agents

    def get_tasks_and_agents(self, agents_list=None) -> tuple[list, list]:
        """Get tasks and agents for the sequential crew.

        Args:
            agents_list: Optional list of additional agents.

        Returns:
            tuple[list, list]: Tuple of (tasks, agents).
        """
        logger.debug(
            i18n.t('components.crewai.sequential_crew.logs.getting_tasks_agents'))

        # Use the agents property to derive agents
        if not agents_list:
            existing_agents = self.agents
            agents_list = existing_agents + (agents_list or [])
            logger.debug(i18n.t('components.crewai.sequential_crew.logs.using_derived_agents',
                                count=len(existing_agents)))

        return super().get_tasks_and_agents(agents_list=agents_list)

    def build_crew(self) -> Message:
        """Build a sequential crew with tasks executed in order.

        Returns:
            Crew: Configured sequential CrewAI crew instance.

        Raises:
            ImportError: If CrewAI is not installed.
            ValueError: If crew creation fails.
        """
        try:
            from crewai import Crew, Process
            logger.debug(
                i18n.t('components.crewai.sequential_crew.logs.imports_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.crewai.sequential_crew.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(
                i18n.t('components.crewai.sequential_crew.logs.building_crew'))
            self.status = i18n.t(
                'components.crewai.sequential_crew.status.building')

            logger.debug(
                i18n.t('components.crewai.sequential_crew.logs.getting_tasks_agents_build'))
            tasks, agents = self.get_tasks_and_agents()

            logger.info(i18n.t('components.crewai.sequential_crew.logs.retrieved_items',
                               task_count=len(tasks),
                               agent_count=len(agents)))

            logger.info(i18n.t('components.crewai.sequential_crew.logs.creating_sequential_crew',
                               agent_count=len(agents),
                               task_count=len(tasks)))

            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=self.verbose,
                memory=self.memory,
                cache=self.use_cache,
                max_rpm=self.max_rpm,
                share_crew=self.share_crew,
                function_calling_llm=self.function_calling_llm,
                step_callback=self.get_step_callback(),
                task_callback=self.get_task_callback(),
            )

            success_msg = i18n.t('components.crewai.sequential_crew.status.crew_created',
                                 agent_count=len(agents),
                                 task_count=len(tasks))
            self.status = success_msg
            logger.info(success_msg)

            return crew

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.crewai.sequential_crew.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
