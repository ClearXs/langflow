import inspect
from abc import ABC

import i18n
import graph_retriever.strategies as strategies_module
from langchain_graph_retriever import GraphRetriever

from lfx.base.vectorstores.model import LCVectorStoreComponent
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import DropdownInput, HandleInput, MultilineInput, NestedDictInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


def traversal_strategies() -> list[str]:
    """Retrieves a list of class names from the strategies_module.

    This function uses the `inspect` module to get all the class members
    from the `strategies_module` and returns their names as a list of strings.

    Returns:
        list[str]: A list of strategy class names.
    """
    try:
        classes = inspect.getmembers(strategies_module, inspect.isclass)
        strategies = [name for name,
                      cls in classes if ABC not in cls.__bases__]
        logger.debug(i18n.t('components.datastax.graph_rag.logs.strategies_loaded',
                            count=len(strategies)))
        return strategies
    except Exception as e:
        logger.error(i18n.t('components.datastax.graph_rag.errors.strategies_load_failed',
                            error=str(e)))
        return []


class GraphRAGComponent(LCVectorStoreComponent):
    """GraphRAGComponent is a component for performing Graph RAG traversal in a vector store.

    Attributes:
        display_name (str): The display name of the component.
        description (str): A brief description of the component.
        name (str): The name of the component.
        icon (str): The icon representing the component.
        inputs (list): A list of input configurations for the component.

    Methods:
        _build_search_args():
            Builds the arguments required for the search operation.
        search_documents() -> list[Data]:
            Searches for documents using the specified strategy, edge definition, and query.
        _edge_definition_from_input() -> tuple:
            Processes the edge definition input and returns it as a tuple.
    """

    display_name: str = i18n.t('components.datastax.graph_rag.display_name')
    description: str = i18n.t('components.datastax.graph_rag.description')
    name = "Graph RAG"
    icon: str = "AstraDB"

    inputs = [
        HandleInput(
            name="embedding_model",
            display_name=i18n.t(
                'components.datastax.graph_rag.embedding_model.display_name'),
            input_types=["Embeddings"],
            info=i18n.t('components.datastax.graph_rag.embedding_model.info'),
            required=False,
        ),
        HandleInput(
            name="vector_store",
            display_name=i18n.t(
                'components.datastax.graph_rag.vector_store.display_name'),
            input_types=["VectorStore"],
            info=i18n.t('components.datastax.graph_rag.vector_store.info'),
        ),
        StrInput(
            name="edge_definition",
            display_name=i18n.t(
                'components.datastax.graph_rag.edge_definition.display_name'),
            info=i18n.t('components.datastax.graph_rag.edge_definition.info'),
        ),
        DropdownInput(
            name="strategy",
            display_name=i18n.t(
                'components.datastax.graph_rag.strategy.display_name'),
            options=traversal_strategies(),
        ),
        MultilineInput(
            name="search_query",
            display_name=i18n.t(
                'components.datastax.graph_rag.search_query.display_name'),
            tool_mode=True,
        ),
        NestedDictInput(
            name="graphrag_strategy_kwargs",
            display_name=i18n.t(
                'components.datastax.graph_rag.graphrag_strategy_kwargs.display_name'),
            info=i18n.t(
                'components.datastax.graph_rag.graphrag_strategy_kwargs.info'),
            advanced=True,
        ),
    ]

    def search_documents(self) -> list[Data]:
        """Searches for documents using the graph retriever based on the selected strategy, edge definition, and query.

        Returns:
            list[Data]: A list of retrieved documents.

        Raises:
            AttributeError: If there is an issue with attribute access.
            TypeError: If there is a type mismatch.
            ValueError: If there is a value error.
        """
        try:
            logger.info(i18n.t('components.datastax.graph_rag.logs.searching_documents',
                               strategy=self.strategy,
                               edge_definition=self.edge_definition))
            self.status = i18n.t(
                'components.datastax.graph_rag.status.searching')

            additional_params = self.graphrag_strategy_kwargs or {}
            logger.debug(i18n.t('components.datastax.graph_rag.logs.additional_params',
                                params=str(additional_params)))

            # Evaluate edge definition
            edge_def = self._evaluate_edge_definition_input()
            logger.debug(i18n.t('components.datastax.graph_rag.logs.edge_definition_evaluated',
                                edge_def=str(edge_def)))

            # Get strategy class
            try:
                strategy_class = getattr(strategies_module, self.strategy)
                logger.debug(i18n.t('components.datastax.graph_rag.logs.strategy_class_loaded',
                                    strategy=self.strategy))
            except AttributeError as e:
                error_msg = i18n.t('components.datastax.graph_rag.errors.strategy_not_found',
                                   strategy=self.strategy)
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            # Create retriever
            logger.info(
                i18n.t('components.datastax.graph_rag.logs.creating_retriever'))
            retriever = GraphRetriever(
                store=self.vector_store,
                edges=[edge_def],
                strategy=strategy_class(**additional_params),
            )

            # Invoke retriever
            logger.info(i18n.t('components.datastax.graph_rag.logs.invoking_retriever',
                               query=self.search_query))
            docs = retriever.invoke(self.search_query)

            logger.info(i18n.t('components.datastax.graph_rag.logs.documents_retrieved',
                               count=len(docs)))

            data = docs_to_data(docs)
            success_msg = i18n.t('components.datastax.graph_rag.status.search_completed',
                                 count=len(data))
            self.status = success_msg
            logger.info(success_msg)

            return data

        except (AttributeError, TypeError, ValueError) as e:
            error_msg = i18n.t('components.datastax.graph_rag.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _edge_definition_from_input(self) -> tuple:
        """Generates the edge definition from the input data.

        Returns:
            tuple: A tuple representing the edge definition.

        Raises:
            ValueError: If edge definition format is invalid.
        """
        try:
            if not self.edge_definition:
                error_msg = i18n.t(
                    'components.datastax.graph_rag.errors.edge_definition_empty')
                logger.error(error_msg)
                raise ValueError(error_msg)

            values = self.edge_definition.split(",")
            values = [value.strip() for value in values]

            logger.debug(i18n.t('components.datastax.graph_rag.logs.edge_definition_parsed',
                                values=str(values)))

            return tuple(values)

        except Exception as e:
            error_msg = i18n.t('components.datastax.graph_rag.errors.edge_definition_parse_failed',
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _evaluate_edge_definition_input(self) -> tuple:
        """Evaluates the edge definition, converting any function calls from strings.

        Args:
            edge_definition (tuple): The edge definition to evaluate.

        Returns:
            tuple: The evaluated edge definition.

        Raises:
            ImportError: If required module cannot be imported.
            ValueError: If evaluation fails.
        """
        try:
            from graph_retriever.edges.metadata import Id
            logger.debug(
                i18n.t('components.datastax.graph_rag.logs.id_module_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.graph_rag.errors.id_module_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            evaluated_values = []
            edge_def = self._edge_definition_from_input()

            for value in edge_def:
                if value == "Id()":
                    # Evaluate Id() as a function call
                    evaluated_values.append(Id())
                    logger.debug(
                        i18n.t('components.datastax.graph_rag.logs.id_function_evaluated'))
                else:
                    evaluated_values.append(value)
                    logger.debug(i18n.t('components.datastax.graph_rag.logs.value_added',
                                        value=value))

            result = tuple(evaluated_values)
            logger.debug(i18n.t('components.datastax.graph_rag.logs.edge_definition_evaluation_completed',
                                result=str(result)))
            return result

        except Exception as e:
            error_msg = i18n.t('components.datastax.graph_rag.errors.edge_definition_evaluation_failed',
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e
