import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackObjectDetectionComponent(Component):
    display_name = "Object Detection"
    description = i18n.t('components.jigsawstack.object_detection.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/object-detection"
    icon = "JigsawStack"
    name = "JigsawStackObjectDetection"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.api_key.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="prompts",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.prompts.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.prompts.info'),
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="url",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.url.display_name'),
            info=i18n.t('components.jigsawstack.object_detection.url.info'),
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="file_store_key",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.file_store_key.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.file_store_key.info'),
            required=False,
            tool_mode=True,
        ),
        BoolInput(
            name="annotated_image",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.annotated_image.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.annotated_image.info'),
            required=False,
            value=True,
        ),
        DropdownInput(
            name="features",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.features.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.features.info'),
            required=False,
            options=["object_detection", "gui"],
            value=["object_detection", "gui"],
        ),
        DropdownInput(
            name="return_type",
            display_name=i18n.t(
                'components.jigsawstack.object_detection.return_type.display_name'),
            info=i18n.t(
                'components.jigsawstack.object_detection.return_type.info'),
            required=False,
            options=["url", "base64"],
            value="url",
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.object_detection.outputs.results.display_name'),
            name="object_detection_results",
            method="detect_objects"
        ),
    ]

    def detect_objects(self) -> Data:
        """Perform object detection on images.

        Returns:
            Data: Detection results with bounding boxes and annotations.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If parameters are invalid.
        """
        logger.info(
            i18n.t('components.jigsawstack.object_detection.logs.starting_detection'))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.object_detection.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.debug(
                i18n.t('components.jigsawstack.object_detection.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Build request object
            params = {}

            # Process prompts
            if self.prompts:
                logger.debug(
                    i18n.t('components.jigsawstack.object_detection.logs.processing_prompts'))

                if isinstance(self.prompts, list):
                    params["prompt"] = self.prompts
                    logger.debug(i18n.t('components.jigsawstack.object_detection.logs.prompts_list',
                                        count=len(self.prompts)))
                elif isinstance(self.prompts, str):
                    if "," in self.prompts:
                        # Split by comma and strip whitespace
                        params["prompt"] = [p.strip()
                                            for p in self.prompts.split(",")]
                        logger.debug(i18n.t('components.jigsawstack.object_detection.logs.prompts_split',
                                            count=len(params["prompt"])))
                    else:
                        params["prompt"] = [self.prompts.strip()]
                        logger.debug(
                            i18n.t('components.jigsawstack.object_detection.logs.prompts_single'))
                else:
                    error_msg = i18n.t(
                        'components.jigsawstack.object_detection.errors.invalid_prompt')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(i18n.t('components.jigsawstack.object_detection.logs.prompts_parsed',
                                    prompts=", ".join(params["prompt"])))

            # Process image source
            if self.url:
                params["url"] = self.url
                logger.debug(i18n.t('components.jigsawstack.object_detection.logs.using_url',
                                    url=self.url))

            if self.file_store_key:
                params["file_store_key"] = self.file_store_key
                logger.debug(i18n.t('components.jigsawstack.object_detection.logs.using_file_store_key',
                                    key=self.file_store_key))

            # Validate image source
            if not self.url and not self.file_store_key:
                error_msg = i18n.t(
                    'components.jigsawstack.object_detection.errors.missing_image_source')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Set other parameters
            params["annotated_image"] = self.annotated_image
            logger.debug(i18n.t('components.jigsawstack.object_detection.logs.annotated_image_setting',
                                enabled=self.annotated_image))

            if self.features:
                params["features"] = self.features
                logger.debug(i18n.t('components.jigsawstack.object_detection.logs.features_enabled',
                                    features=", ".join(self.features)))

            if self.return_type:
                params["return_type"] = self.return_type
                logger.debug(i18n.t('components.jigsawstack.object_detection.logs.return_type_setting',
                                    type=self.return_type))

            # Call object detection
            logger.info(
                i18n.t('components.jigsawstack.object_detection.logs.calling_api'))
            response = client.vision.object_detection(params)

            if not response.get("success", False):
                error_msg = i18n.t(
                    'components.jigsawstack.object_detection.errors.api_request_failed')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log detection results
            objects_count = len(response.get("objects", []))
            has_annotated = "annotated_image_url" in response

            logger.info(i18n.t('components.jigsawstack.object_detection.logs.detection_complete',
                               count=objects_count,
                               has_annotated=has_annotated))

            status_msg = i18n.t('components.jigsawstack.object_detection.logs.detection_success',
                                count=objects_count)
            self.status = status_msg

            return Data(data=response)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.object_detection.errors.jigsawstack_error',
                               error=str(e))
            logger.error(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            error_data = {"error": error_msg, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.object_detection.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
