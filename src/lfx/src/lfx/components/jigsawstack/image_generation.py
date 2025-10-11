import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackImageGenerationComponent(Component):
    display_name = "Image Generation"
    description = i18n.t('components.jigsawstack.image_generation.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/image-generation"
    icon = "JigsawStack"
    name = "JigsawStackImageGeneration"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.api_key.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="prompt",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.prompt.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.prompt.info'),
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="aspect_ratio",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.aspect_ratio.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.aspect_ratio.info'),
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="url",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.url.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.url.info'),
            required=False,
        ),
        MessageTextInput(
            name="file_store_key",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.file_store_key.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.file_store_key.info'),
            required=False,
            tool_mode=True,
        ),
        IntInput(
            name="width",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.width.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.width.info'),
            required=False,
        ),
        IntInput(
            name="height",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.height.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.height.info'),
            required=False,
        ),
        IntInput(
            name="steps",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.steps.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.steps.info'),
            required=False,
        ),
        DropdownInput(
            name="output_format",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.output_format.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.output_format.info'),
            required=False,
            options=["png", "svg"],
            value="png",
        ),
        MessageTextInput(
            name="negative_prompt",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.negative_prompt.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.negative_prompt.info'),
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.seed.display_name'),
            info=i18n.t('components.jigsawstack.image_generation.seed.info'),
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        IntInput(
            name="guidance",
            display_name=i18n.t(
                'components.jigsawstack.image_generation.guidance.display_name'),
            info=i18n.t(
                'components.jigsawstack.image_generation.guidance.info'),
            required=False,
            tool_mode=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.image_generation.outputs.results.display_name'),
            name="image_generation_results",
            method="generate_image"
        ),
    ]

    def generate_image(self) -> Data:
        """Generate an image using AI models.

        Returns:
            Data: Generated image URL and metadata.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If parameters are invalid.
        """
        logger.info(
            i18n.t('components.jigsawstack.image_generation.logs.starting_generation'))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.image_generation.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            min_character_length = 1
            max_character_length = 5000
            min_width = 256
            max_width = 1920
            min_height = 256
            max_height = 1920
            min_steps = 1
            max_steps = 90
            min_guidance = 1
            max_guidance = 28

            logger.debug(
                i18n.t('components.jigsawstack.image_generation.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Validate prompt
            if not self.prompt or len(self.prompt) < min_character_length or len(self.prompt) > max_character_length:
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_prompt',
                                   min=min_character_length,
                                   max=max_character_length)
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.jigsawstack.image_generation.logs.prompt_validated',
                                length=len(self.prompt)))

            # Validate aspect ratio
            valid_ratios = ["1:1", "16:9", "21:9", "3:2",
                            "2:3", "4:5", "5:4", "3:4", "4:3", "9:16", "9:21"]
            if self.aspect_ratio and self.aspect_ratio not in valid_ratios:
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_aspect_ratio',
                                   ratios=", ".join(valid_ratios))
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate width
            if self.width and (self.width < min_width or self.width > max_width):
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_width',
                                   min=min_width,
                                   max=max_width)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate height
            if self.height and (self.height < min_height or self.height > max_height):
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_height',
                                   min=min_height,
                                   max=max_height)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate steps
            if self.steps and (self.steps < min_steps or self.steps > max_steps):
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_steps',
                                   min=min_steps,
                                   max=max_steps)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate guidance
            if self.guidance and (self.guidance < min_guidance or self.guidance > max_guidance):
                error_msg = i18n.t('components.jigsawstack.image_generation.errors.invalid_guidance',
                                   min=min_guidance,
                                   max=max_guidance)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Build parameters
            params = {}
            if self.prompt:
                params["prompt"] = self.prompt.strip()
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_prompt',
                                    prompt=self.prompt.strip()[:100]))

            if self.aspect_ratio:
                params["aspect_ratio"] = self.aspect_ratio.strip()
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_aspect_ratio',
                                    ratio=self.aspect_ratio.strip()))

            if self.url:
                params["url"] = self.url.strip()
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_webhook_url',
                                    url=self.url.strip()))

            if self.file_store_key:
                params["file_store_key"] = self.file_store_key.strip()
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_file_store_key',
                                    key=self.file_store_key.strip()))

            if self.width:
                params["width"] = self.width
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_width',
                                    width=self.width))

            if self.height:
                params["height"] = self.height
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_height',
                                    height=self.height))

            params["return_type"] = "url"

            if self.output_format:
                params["output_format"] = self.output_format.strip()
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_format',
                                    format=self.output_format.strip()))

            if self.steps:
                params["steps"] = self.steps
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_steps',
                                    steps=self.steps))

            # Initialize advance_config if any advanced parameters are provided
            if self.negative_prompt or self.seed or self.guidance:
                params["advance_config"] = {}
                logger.debug(
                    i18n.t('components.jigsawstack.image_generation.logs.using_advanced_config'))

            if self.negative_prompt:
                params["advance_config"]["negative_prompt"] = self.negative_prompt
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_negative_prompt',
                                    prompt=self.negative_prompt[:100]))

            if self.seed:
                params["advance_config"]["seed"] = self.seed
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_seed',
                                    seed=self.seed))

            if self.guidance:
                params["advance_config"]["guidance"] = self.guidance
                logger.debug(i18n.t('components.jigsawstack.image_generation.logs.using_guidance',
                                    guidance=self.guidance))

            # Call image generation
            logger.info(
                i18n.t('components.jigsawstack.image_generation.logs.calling_api'))
            response = client.image_generation(params)

            if response.get("url", None) is None or response.get("url", None).strip() == "":
                error_msg = i18n.t(
                    'components.jigsawstack.image_generation.errors.no_url_returned')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(i18n.t('components.jigsawstack.image_generation.logs.generation_complete',
                               url=response.get("url", "N/A")))

            status_msg = i18n.t(
                'components.jigsawstack.image_generation.logs.generation_success')
            self.status = status_msg

            return Data(data=response)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.image_generation.errors.jigsawstack_error',
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
            error_msg = i18n.t('components.jigsawstack.image_generation.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
