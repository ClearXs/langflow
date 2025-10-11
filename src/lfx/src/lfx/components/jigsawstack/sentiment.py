import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.message import Message


class JigsawStackSentimentComponent(Component):
    display_name = "Sentiment Analysis"
    description = i18n.t('components.jigsawstack.sentiment.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/sentiment"
    icon = "JigsawStack"
    name = "JigsawStackSentiment"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.sentiment.api_key.display_name'),
            info=i18n.t('components.jigsawstack.sentiment.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="text",
            display_name=i18n.t(
                'components.jigsawstack.sentiment.text.display_name'),
            info=i18n.t('components.jigsawstack.sentiment.text.info'),
            required=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.sentiment.outputs.sentiment_data.display_name'),
            name="sentiment_data",
            method="analyze_sentiment"
        ),
        Output(
            display_name=i18n.t(
                'components.jigsawstack.sentiment.outputs.sentiment_text.display_name'),
            name="sentiment_text",
            method="get_sentiment_text"
        ),
    ]

    def analyze_sentiment(self) -> Data:
        """Analyze sentiment of text using AI.

        Returns:
            Data: Sentiment analysis results with scores and emotions.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If API request fails.
        """
        logger.info(i18n.t('components.jigsawstack.sentiment.logs.starting_analysis',
                           text_length=len(self.text)))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.sentiment.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.text or not self.text.strip():
                error_msg = i18n.t(
                    'components.jigsawstack.sentiment.errors.empty_text')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(
                i18n.t('components.jigsawstack.sentiment.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            logger.debug(i18n.t('components.jigsawstack.sentiment.logs.analyzing_text',
                                preview=self.text[:100]))

            logger.info(
                i18n.t('components.jigsawstack.sentiment.logs.calling_api'))
            response = client.sentiment({"text": self.text})

            if not response.get("success", False):
                error_msg = i18n.t(
                    'components.jigsawstack.sentiment.errors.api_request_failed')
                logger.error(error_msg)
                raise ValueError(error_msg)

            sentiment_data = response.get("sentiment", {})
            sentences = response.get("sentences", [])

            sentiment = sentiment_data.get("sentiment", "Unknown")
            emotion = sentiment_data.get("emotion", "Unknown")
            score = sentiment_data.get("score", 0.0)

            logger.info(i18n.t('components.jigsawstack.sentiment.logs.analysis_complete',
                               sentiment=sentiment,
                               emotion=emotion,
                               score=score,
                               sentence_count=len(sentences)))

            result_data = {
                "text_analyzed": self.text,
                "sentiment": sentiment,
                "emotion": emotion,
                "score": score,
                "sentences": sentences,
                "success": True,
            }

            status_msg = i18n.t('components.jigsawstack.sentiment.logs.analysis_summary',
                                sentiment=sentiment,
                                emotion=emotion,
                                score=score)
            self.status = status_msg

            return Data(data=result_data)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.sentiment.errors.jigsawstack_error',
                               error=str(e))
            logger.error(error_msg)
            error_data = {"error": str(
                e), "text_analyzed": self.text, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            error_data = {"error": error_msg,
                          "text_analyzed": self.text, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.sentiment.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(
                e), "text_analyzed": self.text, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

    def get_sentiment_text(self) -> Message:
        """Get formatted sentiment analysis results as text.

        Returns:
            Message: Formatted sentiment analysis results.
        """
        logger.info(
            i18n.t('components.jigsawstack.sentiment.logs.generating_text_output'))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError:
            error_msg = i18n.t(
                'components.jigsawstack.sentiment.errors.import_error')
            logger.error(error_msg)
            return Message(text=error_msg)

        try:
            logger.debug(
                i18n.t('components.jigsawstack.sentiment.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            logger.info(
                i18n.t('components.jigsawstack.sentiment.logs.calling_api'))
            response = client.sentiment({"text": self.text})

            sentiment_data = response.get("sentiment", {})
            sentences = response.get("sentences", [])

            sentiment = sentiment_data.get("sentiment", "Unknown")
            emotion = sentiment_data.get("emotion", "Unknown")
            score = sentiment_data.get("score", 0.0)

            # Format the output with i18n
            formatted_output = i18n.t(
                'components.jigsawstack.sentiment.output.header')
            formatted_output += "\n\n"
            formatted_output += i18n.t('components.jigsawstack.sentiment.output.text',
                                       text=self.text)
            formatted_output += "\n\n"
            formatted_output += i18n.t('components.jigsawstack.sentiment.output.overall_sentiment',
                                       sentiment=sentiment)
            formatted_output += "\n"
            formatted_output += i18n.t('components.jigsawstack.sentiment.output.emotion',
                                       emotion=emotion)
            formatted_output += "\n"
            formatted_output += i18n.t('components.jigsawstack.sentiment.output.score',
                                       score=f"{score:.3f}")
            formatted_output += "\n\n"
            formatted_output += i18n.t(
                'components.jigsawstack.sentiment.output.sentence_analysis')
            formatted_output += "\n"

            for i, sentence in enumerate(sentences, 1):
                sentence_text = sentence.get("text", "")
                sentence_sentiment = sentence.get("sentiment", "Unknown")
                sentence_emotion = sentence.get("emotion", "Unknown")
                sentence_score = sentence.get("score", 0.0)

                formatted_output += i18n.t('components.jigsawstack.sentiment.output.sentence_item',
                                           index=i,
                                           text=sentence_text,
                                           sentiment=sentence_sentiment,
                                           emotion=sentence_emotion,
                                           score=f"{sentence_score:.3f}")
                formatted_output += "\n"

            logger.info(
                i18n.t('components.jigsawstack.sentiment.logs.text_output_generated'))
            return Message(text=formatted_output)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.sentiment.errors.analysis_error',
                               error=str(e))
            logger.error(error_msg)
            return Message(text=error_msg)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.sentiment.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            return Message(text=error_msg)
