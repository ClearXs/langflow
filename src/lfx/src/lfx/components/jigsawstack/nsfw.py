import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackNSFWComponent(Component):
    display_name = "NSFW Detection"
    description = i18n.t('components.jigsawstack.nsfw.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/nsfw"
    icon = "JigsawStack"
    name = "JigsawStackNSFW"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.nsfw.api_key.display_name'),
            info=i18n.t('components.jigsawstack.nsfw.api_key.info'),
            required=True,
        ),
        StrInput(
            name="url",
            display_name=i18n.t(
                'components.jigsawstack.nsfw.url.display_name'),
            info=i18n.t('components.jigsawstack.nsfw.url.info'),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.nsfw.outputs.nsfw_result.display_name'),
            name="nsfw_result",
            method="detect_nsfw"
        ),
    ]

    def detect_nsfw(self) -> Data:
        """Detect NSFW content in image or video.

        Returns:
            Data: NSFW detection results with confidence scores.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If URL is invalid or API request fails.
        """
        logger.info(i18n.t('components.jigsawstack.nsfw.logs.starting_detection',
                           url=self.url))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.nsfw.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.url or not self.url.strip():
                error_msg = i18n.t(
                    'components.jigsawstack.nsfw.errors.empty_url')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(
                i18n.t('components.jigsawstack.nsfw.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Build request parameters
            params = {"url": self.url.strip()}

            logger.debug(i18n.t('components.jigsawstack.nsfw.logs.analyzing_url',
                                url=params["url"]))

            logger.info(i18n.t('components.jigsawstack.nsfw.logs.calling_api'))
            response = client.validate.nsfw(params)

            if not response.get("success", False):
                error_msg = i18n.t(
                    'components.jigsawstack.nsfw.errors.api_request_failed')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log detection results
            is_nsfw = response.get("is_nsfw", False)
            confidence = response.get("confidence", 0)

            logger.info(i18n.t('components.jigsawstack.nsfw.logs.detection_complete',
                               is_nsfw=is_nsfw,
                               confidence=confidence))

            if is_nsfw:
                status_msg = i18n.t('components.jigsawstack.nsfw.logs.nsfw_detected',
                                    confidence=confidence)
            else:
                status_msg = i18n.t('components.jigsawstack.nsfw.logs.safe_content',
                                    confidence=confidence)

            self.status = status_msg
            logger.info(status_msg)

            return Data(data=response)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            error_data = {"error": error_msg, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.nsfw.errors.jigsawstack_error',
                               error=str(e))
            logger.error(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.nsfw.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
