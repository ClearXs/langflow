import os
import i18n
from lfx.base.agents.crewai.crew import convert_llm, convert_tools
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DictInput, HandleInput, MultilineInput, Output
from lfx.log.logger import logger


class CrewAIAgentComponent(Component):
    """Component for creating a CrewAI agent.

    This component allows you to create a CrewAI agent with the specified role, goal, backstory, tools,
    and language model.

    Args:
        Component (Component): Base class for all components.

    Returns:
        Agent: CrewAI agent.
    """

    display_name = i18n.t('components.crewai.crewai.display_name')
    description = i18n.t('components.crewai.crewai.description')
    documentation: str = "https://docs.crewai.com/how-to/LLM-Connections/"
    icon = "CrewAI"
    legacy = True
    replacement = "agents.Agent"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MultilineInput(
            name="role",
            display_name=i18n.t('components.crewai.crewai.role.display_name'),
            info=i18n.t('components.crewai.crewai.role.info')
        ),
        MultilineInput(
            name="goal",
            display_name=i18n.t('components.crewai.crewai.goal.display_name'),
            info=i18n.t('components.crewai.crewai.goal.info')
        ),
        MultilineInput(
            name="backstory",
            display_name=i18n.t(
                'components.crewai.crewai.backstory.display_name'),
            info=i18n.t('components.crewai.crewai.backstory.info')
        ),
        HandleInput(
            name="tools",
            display_name=i18n.t('components.crewai.crewai.tools.display_name'),
            input_types=["Tool"],
            is_list=True,
            info=i18n.t('components.crewai.crewai.tools.info'),
            value=[],
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t('components.crewai.crewai.llm.display_name'),
            info=i18n.t('components.crewai.crewai.llm.info'),
            input_types=["LanguageModel"],
        ),
        BoolInput(
            name="memory",
            display_name=i18n.t(
                'components.crewai.crewai.memory.display_name'),
            info=i18n.t('components.crewai.crewai.memory.info'),
            advanced=True,
            value=True,
        ),
        BoolInput(
            name="verbose",
            display_name=i18n.t(
                'components.crewai.crewai.verbose.display_name'),
            advanced=True,
            value=False,
        ),
        BoolInput(
            name="allow_delegation",
            display_name=i18n.t(
                'components.crewai.crewai.allow_delegation.display_name'),
            info=i18n.t('components.crewai.crewai.allow_delegation.info'),
            value=True,
        ),
        BoolInput(
            name="allow_code_execution",
            display_name=i18n.t(
                'components.crewai.crewai.allow_code_execution.display_name'),
            info=i18n.t('components.crewai.crewai.allow_code_execution.info'),
            value=False,
            advanced=True,
        ),
        DictInput(
            name="kwargs",
            display_name=i18n.t(
                'components.crewai.crewai.kwargs.display_name'),
            info=i18n.t('components.crewai.crewai.kwargs.info'),
            is_list=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.crewai.crewai.outputs.agent.display_name'),
            name="output",
            method="build_output"
        ),
    ]

    def build_output(self):
        """Build and return a CrewAI agent.

        Returns:
            Agent: Configured CrewAI agent instance.

        Raises:
            ImportError: If CrewAI is not installed.
            ValueError: If agent creation fails.
        """
        try:
            from crewai import Agent
            logger.debug(
                i18n.t('components.crewai.crewai.logs.imports_successful'))
        except ImportError as e:
            error_msg = i18n.t('components.crewai.crewai.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(i18n.t('components.crewai.crewai.logs.creating_agent',
                               role=self.role))
            self.status = i18n.t(
                'components.crewai.crewai.status.creating_agent')

            kwargs = self.kwargs or {}

            # Convert LLM and tools
            logger.debug(
                i18n.t('components.crewai.crewai.logs.converting_llm'))
            converted_llm = convert_llm(self.llm)

            logger.debug(i18n.t('components.crewai.crewai.logs.converting_tools',
                                count=len(self.tools) if self.tools else 0))
            converted_tools = convert_tools(self.tools)

            # Define the Agent
            agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                llm=converted_llm,
                verbose=self.verbose,
                memory=self.memory,
                tools=converted_tools,
                allow_delegation=self.allow_delegation,
                allow_code_execution=self.allow_code_execution,
                **kwargs,
            )

            success_msg = i18n.t('components.crewai.crewai.status.agent_created',
                                 role=self.role)
            self.status = repr(agent)
            logger.info(success_msg)

            return agent

        except Exception as e:
            error_msg = i18n.t('components.crewai.crewai.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
