import os
from pathlib import Path
from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger


class S3BucketUploaderComponent(Component):
    """S3BucketUploaderComponent is a component responsible for uploading files to an S3 bucket.

    It provides two strategies for file upload: "Store Data" and "Store Original File". The component
    requires AWS credentials and bucket details as inputs and processes files accordingly.

    Attributes:
        display_name (str): The display name of the component.
        description (str): A brief description of the components functionality.
        icon (str): The icon representing the component.
        name (str): The internal name of the component.
        inputs (list): A list of input configurations required by the component.
        outputs (list): A list of output configurations provided by the component.

    Methods:
        process_files() -> None:
            Processes files based on the selected strategy. Calls the appropriate method
            based on the strategy attribute.
        process_files_by_data() -> None:
            Processes and uploads files to an S3 bucket based on the data inputs. Iterates
            over the data inputs, logs the file path and text content, and uploads each file
            to the specified S3 bucket if both file path and text content are available.
        process_files_by_name() -> None:
            Processes and uploads files to an S3 bucket based on their names. Iterates through
            the list of data inputs, retrieves the file path from each data item, and uploads
            the file to the specified S3 bucket if the file path is available. Logs the file
            path being uploaded.
        _s3_client() -> Any:
            Creates and returns an S3 client using the provided AWS access key ID and secret
            access key.

        Please note that this component requires the boto3 library to be installed. It is designed
        to work with File and Director components as inputs
    """

    display_name = i18n.t('components.amazon.s3_bucket_uploader.display_name')
    description = i18n.t('components.amazon.s3_bucket_uploader.description')
    icon = "Amazon"
    name = "s3bucketuploader"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="aws_access_key_id",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.aws_access_key_id.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.amazon.s3_bucket_uploader.aws_access_key_id.info'),
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.aws_secret_access_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.amazon.s3_bucket_uploader.aws_secret_access_key.info'),
        ),
        StrInput(
            name="bucket_name",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.bucket_name.display_name'),
            info=i18n.t(
                'components.amazon.s3_bucket_uploader.bucket_name.info'),
            advanced=False,
        ),
        DropdownInput(
            name="strategy",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.strategy.display_name'),
            options=[
                i18n.t(
                    'components.amazon.s3_bucket_uploader.strategy.options.store_data'),
                i18n.t(
                    'components.amazon.s3_bucket_uploader.strategy.options.store_original_file')
            ],
            value=i18n.t(
                'components.amazon.s3_bucket_uploader.strategy.options.store_data'),
            info=i18n.t('components.amazon.s3_bucket_uploader.strategy.info'),
        ),
        HandleInput(
            name="data_inputs",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.data_inputs.display_name'),
            info=i18n.t(
                'components.amazon.s3_bucket_uploader.data_inputs.info'),
            input_types=["Data"],
            is_list=True,
            required=True,
        ),
        StrInput(
            name="s3_prefix",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.s3_prefix.display_name'),
            info=i18n.t('components.amazon.s3_bucket_uploader.s3_prefix.info'),
            advanced=True,
        ),
        BoolInput(
            name="strip_path",
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.strip_path.display_name'),
            info=i18n.t(
                'components.amazon.s3_bucket_uploader.strip_path.info'),
            required=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.amazon.s3_bucket_uploader.outputs.data.display_name'),
            name="data",
            method="process_files"
        ),
    ]

    def process_files(self) -> None:
        """Process files based on the selected strategy.

        This method uses a strategy pattern to process files. The strategy is determined
        by the `self.strategy` attribute, which can be either "Store Data" or "Store Original File".
        Depending on the strategy, the corresponding method (`process_files_by_data` or
        `process_files_by_name`) is called. If an invalid strategy is provided, an error
        is logged.

        Returns:
            None
        """
        try:
            self.status = i18n.t(
                'components.amazon.s3_bucket_uploader.status.processing_files')

            # Get localized strategy names
            store_data = i18n.t(
                'components.amazon.s3_bucket_uploader.strategy.options.store_data')
            store_original = i18n.t(
                'components.amazon.s3_bucket_uploader.strategy.options.store_original_file')

            strategy_methods = {
                "Store Data": self.process_files_by_data,
                "Store Original File": self.process_files_by_name,
                store_data: self.process_files_by_data,
                store_original: self.process_files_by_name,
            }

            method = strategy_methods.get(self.strategy)
            if method:
                method()
            else:
                error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.invalid_strategy',
                                   strategy=self.strategy)
                logger.error(error_msg)
                self.status = error_msg

        except Exception as e:
            error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.process_files_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise

    def process_files_by_data(self) -> None:
        """Processes and uploads files to an S3 bucket based on the data inputs.

        This method iterates over the data inputs, logs the file path and text content,
        and uploads each file to the specified S3 bucket if both file path and text content
        are available.

        Args:
            None

        Returns:
            None
        """
        try:
            if not self.data_inputs:
                warning_msg = i18n.t(
                    'components.amazon.s3_bucket_uploader.warnings.no_data_inputs')
                logger.warning(warning_msg)
                self.status = warning_msg
                return

            uploaded_count = 0
            skipped_count = 0

            for data_item in self.data_inputs:
                try:
                    file_path = data_item.data.get("file_path")
                    text_content = data_item.data.get("text")

                    if file_path and text_content:
                        normalized_path = self._normalize_path(file_path)

                        logger.info(i18n.t('components.amazon.s3_bucket_uploader.logs.uploading_data',
                                           path=file_path, key=normalized_path))

                        self._s3_client().put_object(
                            Bucket=self.bucket_name,
                            Key=normalized_path,
                            Body=text_content
                        )

                        uploaded_count += 1
                        logger.info(i18n.t('components.amazon.s3_bucket_uploader.logs.data_uploaded',
                                           key=normalized_path))
                    else:
                        skipped_count += 1
                        logger.warning(i18n.t('components.amazon.s3_bucket_uploader.warnings.missing_data',
                                              path=file_path or 'unknown'))

                except Exception as e:
                    error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.upload_data_failed',
                                       path=file_path if 'file_path' in locals() else 'unknown',
                                       error=str(e))
                    logger.error(error_msg)
                    # Continue processing other files

            success_msg = i18n.t('components.amazon.s3_bucket_uploader.success.files_processed_by_data',
                                 uploaded=uploaded_count, skipped=skipped_count)
            logger.info(success_msg)
            self.status = success_msg

        except Exception as e:
            error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.process_by_data_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise

    def process_files_by_name(self) -> None:
        """Processes and uploads files to an S3 bucket based on their names.

        Iterates through the list of data inputs, retrieves the file path from each data item,
        and uploads the file to the specified S3 bucket if the file path is available.
        Logs the file path being uploaded.

        Returns:
            None
        """
        try:
            if not self.data_inputs:
                warning_msg = i18n.t(
                    'components.amazon.s3_bucket_uploader.warnings.no_data_inputs')
                logger.warning(warning_msg)
                self.status = warning_msg
                return

            uploaded_count = 0
            skipped_count = 0

            for data_item in self.data_inputs:
                try:
                    file_path = data_item.data.get("file_path")

                    if file_path:
                        # Verify file exists
                        if not Path(file_path).exists():
                            skipped_count += 1
                            logger.warning(i18n.t('components.amazon.s3_bucket_uploader.warnings.file_not_found',
                                                  path=file_path))
                            continue

                        normalized_path = self._normalize_path(file_path)

                        logger.info(i18n.t('components.amazon.s3_bucket_uploader.logs.uploading_file',
                                           path=file_path, key=normalized_path))

                        self._s3_client().upload_file(
                            file_path,
                            Bucket=self.bucket_name,
                            Key=normalized_path
                        )

                        uploaded_count += 1
                        logger.info(i18n.t('components.amazon.s3_bucket_uploader.logs.file_uploaded',
                                           key=normalized_path))
                    else:
                        skipped_count += 1
                        logger.warning(
                            i18n.t('components.amazon.s3_bucket_uploader.warnings.no_file_path'))

                except Exception as e:
                    error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.upload_file_failed',
                                       path=file_path if 'file_path' in locals() else 'unknown',
                                       error=str(e))
                    logger.error(error_msg)
                    # Continue processing other files

            success_msg = i18n.t('components.amazon.s3_bucket_uploader.success.files_processed_by_name',
                                 uploaded=uploaded_count, skipped=skipped_count)
            logger.info(success_msg)
            self.status = success_msg

        except Exception as e:
            error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.process_by_name_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise

    def _s3_client(self) -> Any:
        """Creates and returns an S3 client using the provided AWS access key ID and secret access key.

        Returns:
            Any: A boto3 S3 client instance.
        """
        try:
            import boto3
        except ImportError as e:
            error_msg = i18n.t(
                'components.amazon.s3_bucket_uploader.errors.boto3_not_installed')
            raise ImportError(error_msg) from e

        try:
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
        except Exception as e:
            error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.s3_client_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    def _normalize_path(self, file_path) -> str:
        """Process the file path based on the s3_prefix and path_as_prefix.

        Args:
            file_path (str): The original file path.

        Returns:
            str: The processed file path.
        """
        try:
            prefix = self.s3_prefix
            strip_path = self.strip_path
            processed_path: str = file_path

            if strip_path:
                # Filename only
                processed_path = Path(file_path).name
                logger.debug(i18n.t('components.amazon.s3_bucket_uploader.logs.path_stripped',
                                    original=file_path, stripped=processed_path))

            # Concatenate the s3_prefix if it exists
            if prefix:
                processed_path = str(Path(prefix) / processed_path)
                logger.debug(i18n.t('components.amazon.s3_bucket_uploader.logs.prefix_added',
                                    prefix=prefix, result=processed_path))

            return processed_path

        except Exception as e:
            error_msg = i18n.t('components.amazon.s3_bucket_uploader.errors.path_normalization_failed',
                               path=file_path, error=str(e))
            logger.error(error_msg)
            # Return original path as fallback
            return file_path
