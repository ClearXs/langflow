import i18n
from lfx.base.agents.crewai.crew import BaseCrewComponent
from lfx.io import HandleInput
from lfx.log.logger import logger


class HierarchicalCrewComponent(BaseCrewComponent):
    display_name: str = i18n.t(
        'components.crewai.hierarchical_crew.display_name')
    description: str = i18n.t(
        'components.crewai.hierarchical_crew.description')
    documentation: str = "https://docs.crewai.com/how-to/Hierarchical/"
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    inputs = [
        *BaseCrewComponent.get_base_inputs(),
        HandleInput(
            name="agents",
            display_name=i18n.t(
                'components.crewai.hierarchical_crew.agents.display_name'),
            input_types=["Agent"],
            is_list=True,
            info=i18n.t('components.crewai.hierarchical_crew.agents.info')
        ),
        HandleInput(
            name="tasks",
            display_name=i18n.t(
                'components.crewai.hierarchical_crew.tasks.display_name'),
            input_types=["HierarchicalTask"],
            is_list=True,
            info=i18n.t('components.crewai.hierarchical_crew.tasks.info')
        ),
        HandleInput(
            name="manager_llm",
            display_name=i18n.t(
                'components.crewai.hierarchical_crew.manager_llm.display_name'),
            input_types=["LanguageModel"],
            required=False,
            info=i18n.t('components.crewai.hierarchical_crew.manager_llm.info')
        ),
        HandleInput(
            name="manager_agent",
            display_name=i18n.t(
                'components.crewai.hierarchical_crew.manager_agent.display_name'),
            input_types=["Agent"],
            required=False,
            info=i18n.t(
                'components.crewai.hierarchical_crew.manager_agent.info')
        ),
    ]

    def build_crew(self):
        """Build a hierarchical crew with manager-agent structure.

        Returns:
            Crew: Configured hierarchical CrewAI crew instance.

        Raises:
            ImportError: If CrewAI is not installed.
            ValueError: If crew creation fails.
        """
        try:
            from crewai import Crew, Process
            logger.debug(
                i18n.t('components.crewai.hierarchical_crew.logs.imports_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.crewai.hierarchical_crew.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(
                i18n.t('components.crewai.hierarchical_crew.logs.building_crew'))
            self.status = i18n.t(
                'components.crewai.hierarchical_crew.status.building')

            logger.debug(
                i18n.t('components.crewai.hierarchical_crew.logs.getting_tasks_agents'))
            tasks, agents = self.get_tasks_and_agents()

            logger.info(i18n.t('components.crewai.hierarchical_crew.logs.retrieved_items',
                               task_count=len(tasks),
                               agent_count=len(agents)))

            logger.debug(
                i18n.t('components.crewai.hierarchical_crew.logs.getting_manager_llm'))
            manager_llm = self.get_manager_llm()

            if manager_llm:
                logger.info(
                    i18n.t('components.crewai.hierarchical_crew.logs.manager_llm_set'))

            if hasattr(self, 'manager_agent') and self.manager_agent:
                logger.info(
                    i18n.t('components.crewai.hierarchical_crew.logs.manager_agent_set'))

            logger.info(i18n.t('components.crewai.hierarchical_crew.logs.creating_hierarchical_crew',
                               agent_count=len(agents),
                               task_count=len(tasks)))

            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.hierarchical,
                verbose=self.verbose,
                memory=self.memory,
                cache=self.use_cache,
                max_rpm=self.max_rpm,
                share_crew=self.share_crew,
                function_calling_llm=self.function_calling_llm,
                manager_agent=self.manager_agent,
                manager_llm=manager_llm,
                step_callback=self.get_step_callback(),
                task_callback=self.get_task_callback(),
            )

            success_msg = i18n.t('components.crewai.hierarchical_crew.status.crew_created',
                                 agent_count=len(agents),
                                 task_count=len(tasks))
            self.status = success_msg
            logger.info(success_msg)

            return crew

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.crewai.hierarchical_crew.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
