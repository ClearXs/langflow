import os
import i18n
from typing import Any

import numpy as np

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class EmbeddingSimilarityComponent(Component):
    display_name: str = i18n.t('components.embeddings.similarity.display_name')
    description: str = i18n.t('components.embeddings.similarity.description')
    icon = "equal"
    legacy: bool = True
    replacement = ["datastax.AstraDB"]

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DataInput(
            name="embedding_vectors",
            display_name=i18n.t(
                'components.embeddings.similarity.embedding_vectors.display_name'),
            info=i18n.t(
                'components.embeddings.similarity.embedding_vectors.info'),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="similarity_metric",
            display_name=i18n.t(
                'components.embeddings.similarity.similarity_metric.display_name'),
            info=i18n.t(
                'components.embeddings.similarity.similarity_metric.info'),
            options=[
                i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.cosine'),
                i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.euclidean'),
                i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.manhattan'),
            ],
            value=i18n.t(
                'components.embeddings.similarity.similarity_metric.options.cosine'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.embeddings.similarity.outputs.similarity_data.display_name'),
            name="similarity_data",
            method="compute_similarity"
        ),
    ]

    def compute_similarity(self) -> Data:
        """Compute similarity between two embedding vectors.

        Returns:
            Data: Data object containing the similarity score and embedding information.

        Raises:
            ValueError: If the number of embedding vectors is not exactly two or dimensions don't match.
        """
        embedding_vectors: list[Data] = self.embedding_vectors

        logger.info(i18n.t('components.embeddings.similarity.logs.computing_similarity',
                           count=len(embedding_vectors)))

        # Assert that the list contains exactly two Data objects
        if len(embedding_vectors) != 2:  # noqa: PLR2004
            error_msg = i18n.t(
                'components.embeddings.similarity.errors.two_vectors_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            embedding_1 = np.array(embedding_vectors[0].data["embeddings"])
            embedding_2 = np.array(embedding_vectors[1].data["embeddings"])

            logger.debug(i18n.t('components.embeddings.similarity.logs.embeddings_extracted',
                                dim1=embedding_1.shape,
                                dim2=embedding_2.shape))
        except KeyError as e:
            error_msg = i18n.t('components.embeddings.similarity.errors.missing_embeddings_key',
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        if embedding_1.shape != embedding_2.shape:
            error_msg = i18n.t('components.embeddings.similarity.errors.dimension_mismatch',
                               dim1=embedding_1.shape,
                               dim2=embedding_2.shape)
            logger.error(error_msg)
            similarity_score: dict[str, Any] = {"error": error_msg}
        else:
            similarity_metric = self.similarity_metric
            logger.debug(i18n.t('components.embeddings.similarity.logs.using_metric',
                                metric=similarity_metric))

            try:
                cosine_label = i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.cosine')
                euclidean_label = i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.euclidean')
                manhattan_label = i18n.t(
                    'components.embeddings.similarity.similarity_metric.options.manhattan')

                if similarity_metric == cosine_label:
                    score = np.dot(embedding_1, embedding_2) / (
                        np.linalg.norm(embedding_1) *
                        np.linalg.norm(embedding_2)
                    )
                    similarity_score = {"cosine_similarity": float(score)}
                    logger.info(i18n.t('components.embeddings.similarity.logs.cosine_computed',
                                       score=float(score)))

                elif similarity_metric == euclidean_label:
                    score = np.linalg.norm(embedding_1 - embedding_2)
                    similarity_score = {"euclidean_distance": float(score)}
                    logger.info(i18n.t('components.embeddings.similarity.logs.euclidean_computed',
                                       score=float(score)))

                elif similarity_metric == manhattan_label:
                    score = np.sum(np.abs(embedding_1 - embedding_2))
                    similarity_score = {"manhattan_distance": float(score)}
                    logger.info(i18n.t('components.embeddings.similarity.logs.manhattan_computed',
                                       score=float(score)))
                else:
                    error_msg = i18n.t('components.embeddings.similarity.errors.unknown_metric',
                                       metric=similarity_metric)
                    logger.error(error_msg)
                    similarity_score = {"error": error_msg}

            except Exception as e:
                error_msg = i18n.t('components.embeddings.similarity.errors.computation_failed',
                                   error=str(e))
                logger.exception(error_msg)
                similarity_score = {"error": error_msg}

        # Create a Data object to encapsulate the similarity score and additional information
        try:
            similarity_data = Data(
                data={
                    "embedding_1": embedding_vectors[0].data["embeddings"],
                    "embedding_2": embedding_vectors[1].data["embeddings"],
                    "similarity_score": similarity_score,
                },
                text_key="similarity_score",
            )

            logger.info(
                i18n.t('components.embeddings.similarity.logs.similarity_data_created'))
            self.status = similarity_data
            return similarity_data

        except Exception as e:
            error_msg = i18n.t('components.embeddings.similarity.errors.data_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
