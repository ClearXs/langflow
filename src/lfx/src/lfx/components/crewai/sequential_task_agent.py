import os
import i18n
from lfx.base.agents.crewai.tasks import SequentialTask
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DictInput, HandleInput, MultilineInput, Output
from lfx.log.logger import logger


class SequentialTaskAgentComponent(Component):
    display_name = i18n.t(
        'components.crewai.sequential_task_agent.display_name')
    description = i18n.t('components.crewai.sequential_task_agent.description')
    documentation = "https://docs.crewai.com/how-to/LLM-Connections/"
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        # Agent inputs
        MultilineInput(
            name="role",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.role.display_name'),
            info=i18n.t('components.crewai.sequential_task_agent.role.info')
        ),
        MultilineInput(
            name="goal",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.goal.display_name'),
            info=i18n.t('components.crewai.sequential_task_agent.goal.info')
        ),
        MultilineInput(
            name="backstory",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.backstory.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.backstory.info'),
        ),
        HandleInput(
            name="tools",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.tools.display_name'),
            input_types=["Tool"],
            is_list=True,
            info=i18n.t('components.crewai.sequential_task_agent.tools.info'),
            value=[],
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.llm.display_name'),
            info=i18n.t('components.crewai.sequential_task_agent.llm.info'),
            input_types=["LanguageModel"],
        ),
        BoolInput(
            name="memory",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.memory.display_name'),
            info=i18n.t('components.crewai.sequential_task_agent.memory.info'),
            advanced=True,
            value=True,
        ),
        BoolInput(
            name="verbose",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.verbose.display_name'),
            advanced=True,
            value=True,
        ),
        BoolInput(
            name="allow_delegation",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.allow_delegation.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.allow_delegation.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="allow_code_execution",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.allow_code_execution.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.allow_code_execution.info'),
            value=False,
            advanced=True,
        ),
        DictInput(
            name="agent_kwargs",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.agent_kwargs.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.agent_kwargs.info'),
            is_list=True,
            advanced=True,
        ),
        # Task inputs
        MultilineInput(
            name="task_description",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.task_description.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.task_description.info'),
        ),
        MultilineInput(
            name="expected_output",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.expected_output.display_name'),
            info=i18n.t(
                'components.crewai.sequential_task_agent.expected_output.info'),
        ),
        BoolInput(
            name="async_execution",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.async_execution.display_name'),
            value=False,
            advanced=True,
            info=i18n.t(
                'components.crewai.sequential_task_agent.async_execution.info'),
        ),
        # Chaining input
        HandleInput(
            name="previous_task",
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.previous_task.display_name'),
            input_types=["SequentialTask"],
            info=i18n.t(
                'components.crewai.sequential_task_agent.previous_task.info'),
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.crewai.sequential_task_agent.outputs.task.display_name'),
            name="task_output",
            method="build_agent_and_task",
        ),
    ]

    def build_agent_and_task(self) -> list[SequentialTask]:
        """Build a CrewAI agent and its associated task.

        Returns:
            list[SequentialTask]: List of sequential tasks including previous tasks if chained.

        Raises:
            ImportError: If CrewAI is not installed.
            ValueError: If agent or task creation fails.
        """
        try:
            from crewai import Agent, Task
            logger.debug(
                i18n.t('components.crewai.sequential_task_agent.logs.imports_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.crewai.sequential_task_agent.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(i18n.t('components.crewai.sequential_task_agent.logs.building_agent_task',
                               role=self.role))
            self.status = i18n.t(
                'components.crewai.sequential_task_agent.status.building')

            # Build the agent
            logger.debug(i18n.t('components.crewai.sequential_task_agent.logs.creating_agent',
                                role=self.role))

            agent_kwargs = self.agent_kwargs or {}
            agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                llm=self.llm,
                verbose=self.verbose,
                memory=self.memory,
                tools=self.tools or [],
                allow_delegation=self.allow_delegation,
                allow_code_execution=self.allow_code_execution,
                **agent_kwargs,
            )

            logger.info(i18n.t('components.crewai.sequential_task_agent.logs.agent_created',
                               role=self.role))

            # Build the task
            logger.debug(
                i18n.t('components.crewai.sequential_task_agent.logs.creating_task'))

            task = Task(
                description=self.task_description,
                expected_output=self.expected_output,
                agent=agent,
                async_execution=self.async_execution,
            )

            logger.info(
                i18n.t('components.crewai.sequential_task_agent.logs.task_created'))

            # If there's a previous task, create a list of tasks
            if self.previous_task:
                logger.debug(
                    i18n.t('components.crewai.sequential_task_agent.logs.chaining_tasks'))
                tasks = [*self.previous_task, task] if isinstance(
                    self.previous_task, list) else [self.previous_task, task]
                logger.info(i18n.t('components.crewai.sequential_task_agent.logs.tasks_chained',
                                   total_count=len(tasks)))
            else:
                logger.debug(
                    i18n.t('components.crewai.sequential_task_agent.logs.single_task'))
                tasks = [task]

            success_msg = i18n.t('components.crewai.sequential_task_agent.status.created',
                                 role=self.role,
                                 task_count=len(tasks))
            self.status = f"Agent: {agent!r}\nTask: {task!r}"
            logger.info(success_msg)

            return tasks

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.crewai.sequential_task_agent.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
