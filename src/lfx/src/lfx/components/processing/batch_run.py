from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
import i18n

import toml  # type: ignore[import-untyped]

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataFrameInput, HandleInput, MessageTextInput, MultilineInput, Output
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable


class BatchRunComponent(Component):
    display_name = i18n.t('components.processing.batch_run.display_name')
    description = i18n.t('components.processing.batch_run.description')
    documentation: str = "https://docs.langflow.org/components-processing#batch-run"
    icon = "List"

    inputs = [
        HandleInput(
            name="model",
            display_name=i18n.t(
                'components.processing.batch_run.model.display_name'),
            info=i18n.t('components.processing.batch_run.model.info'),
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="system_message",
            display_name=i18n.t(
                'components.processing.batch_run.system_message.display_name'),
            info=i18n.t('components.processing.batch_run.system_message.info'),
            required=False,
        ),
        DataFrameInput(
            name="df",
            display_name=i18n.t(
                'components.processing.batch_run.df.display_name'),
            info=i18n.t('components.processing.batch_run.df.info'),
            required=True,
        ),
        MessageTextInput(
            name="column_name",
            display_name=i18n.t(
                'components.processing.batch_run.column_name.display_name'),
            info=i18n.t('components.processing.batch_run.column_name.info'),
            required=False,
            advanced=False,
        ),
        MessageTextInput(
            name="output_column_name",
            display_name=i18n.t(
                'components.processing.batch_run.output_column_name.display_name'),
            info=i18n.t(
                'components.processing.batch_run.output_column_name.info'),
            value="model_response",
            required=False,
            advanced=True,
        ),
        BoolInput(
            name="enable_metadata",
            display_name=i18n.t(
                'components.processing.batch_run.enable_metadata.display_name'),
            info=i18n.t(
                'components.processing.batch_run.enable_metadata.info'),
            value=False,
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.batch_run.outputs.batch_results.display_name'),
            name="batch_results",
            method="run_batch",
            info=i18n.t(
                'components.processing.batch_run.outputs.batch_results.info'),
        ),
    ]

    def _format_row_as_toml(self, row: dict[str, Any]) -> str:
        """Convert a dictionary (row) into a TOML-formatted string."""
        try:
            formatted_dict = {str(col): {"value": str(val)}
                              for col, val in row.items()}
            return toml.dumps(formatted_dict)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.batch_run.errors.toml_formatting_failed', error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _create_base_row(
        self, original_row: dict[str, Any], model_response: str = "", batch_index: int = -1
    ) -> dict[str, Any]:
        """Create a base row with original columns and additional metadata."""
        row = original_row.copy()
        row[self.output_column_name] = model_response
        row["batch_index"] = batch_index
        return row

    def _add_metadata(
        self, row: dict[str, Any], *, success: bool = True, system_msg: str = "", error: str | None = None
    ) -> None:
        """Add metadata to a row if enabled."""
        if not self.enable_metadata:
            return

        if success:
            row["metadata"] = {
                "has_system_message": bool(system_msg),
                "input_length": len(row.get("text_input", "")),
                "response_length": len(row[self.output_column_name]),
                "processing_status": "success",
            }
        else:
            row["metadata"] = {
                "error": error,
                "processing_status": "failed",
            }

    async def run_batch(self) -> DataFrame:
        """Process each row in df[column_name] with the language model asynchronously.

        Returns:
            DataFrame: A new DataFrame containing:
                - All original columns
                - The model's response column (customizable name)
                - 'batch_index' column for processing order
                - 'metadata' (optional)

        Raises:
            ValueError: If the specified column is not found in the DataFrame
            TypeError: If the model is not compatible or input types are wrong
        """
        try:
            model: Runnable = self.model
            system_msg = self.system_message or ""
            df: DataFrame = self.df
            col_name = self.column_name or ""

            # Validate inputs first
            if not isinstance(df, DataFrame):
                error_msg = i18n.t('components.processing.batch_run.errors.invalid_dataframe_type',
                                   actual_type=type(df).__name__)
                self.status = error_msg
                raise TypeError(error_msg)

            if col_name and col_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.batch_run.errors.column_not_found',
                                   column=col_name, available=available_cols)
                self.status = error_msg
                raise ValueError(error_msg)

            # Determine text input for each row
            if col_name:
                user_texts = df[col_name].astype(str).tolist()
                info_msg = i18n.t('components.processing.batch_run.info.processing_column',
                                  column=col_name, count=len(user_texts))
            else:
                user_texts = [
                    self._format_row_as_toml(cast("dict[str, Any]", row))
                    for row in df.to_dict(orient="records")
                ]
                info_msg = i18n.t('components.processing.batch_run.info.processing_all_columns',
                                  count=len(user_texts))

            total_rows = len(user_texts)

            processing_msg = i18n.t('components.processing.batch_run.info.starting_batch',
                                    total=total_rows)
            self.status = processing_msg
            await logger.ainfo(processing_msg)

            # Prepare the batch of conversations
            conversations = [
                [{"role": "system", "content": system_msg},
                    {"role": "user", "content": text}]
                if system_msg
                else [{"role": "user", "content": text}]
                for text in user_texts
            ]

            # Configure the model with project info and callbacks
            model = model.with_config(
                {
                    "run_name": self.display_name,
                    "project_name": self.get_project_name(),
                    "callbacks": self.get_langchain_callbacks(),
                }
            )

            # Process batches and track progress
            responses_with_idx = list(
                zip(
                    range(len(conversations)),
                    await model.abatch(list(conversations)),
                    strict=True,
                )
            )

            # Sort by index to maintain order
            responses_with_idx.sort(key=lambda x: x[0])

            # Build the final data with enhanced metadata
            rows: list[dict[str, Any]] = []
            progress_interval = max(1, total_rows // 10)

            for idx, (original_row, response) in enumerate(
                zip(df.to_dict(orient="records"),
                    responses_with_idx, strict=False)
            ):
                response_text = response[1].content if hasattr(
                    response[1], "content") else str(response[1])
                row = self._create_base_row(
                    cast("dict[str, Any]", original_row), model_response=response_text, batch_index=idx
                )
                self._add_metadata(row, success=True, system_msg=system_msg)
                rows.append(row)

                # Log progress
                if (idx + 1) % progress_interval == 0:
                    progress_msg = i18n.t('components.processing.batch_run.info.processing_progress',
                                          current=idx + 1, total=total_rows)
                    await logger.ainfo(progress_msg)

            success_msg = i18n.t('components.processing.batch_run.success.batch_completed',
                                 total=total_rows)
            self.status = success_msg
            await logger.ainfo(success_msg)

            return DataFrame(rows)

        except (KeyError, AttributeError) as e:
            # Handle data structure and attribute access errors
            error_msg = i18n.t(
                'components.processing.batch_run.errors.data_processing_error', error=str(e))
            self.status = error_msg
            await logger.aerror(error_msg)

            error_row = self._create_base_row(dict.fromkeys(
                df.columns, ""), model_response="", batch_index=-1)
            self._add_metadata(error_row, success=False, error=str(e))
            return DataFrame([error_row])

        except TypeError:
            # Re-raise TypeError as is (already has i18n message)
            raise
        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.batch_run.errors.unexpected_error', error=str(e))
            self.status = error_msg
            await logger.aerror(error_msg)

            # Create error DataFrame with empty columns
            error_row = self._create_base_row(
                {}, model_response="", batch_index=-1)
            self._add_metadata(error_row, success=False, error=str(e))
            return DataFrame([error_row])
