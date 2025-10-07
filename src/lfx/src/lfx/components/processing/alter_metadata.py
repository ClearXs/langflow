import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.io import HandleInput, NestedDictInput, Output, StrInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class AlterMetadataComponent(Component):
    display_name = i18n.t('components.processing.alter_metadata.display_name')
    description = i18n.t('components.processing.alter_metadata.description')
    icon = "merge"
    name = "AlterMetadata"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        HandleInput(
            name="input_value",
            display_name=i18n.t(
                'components.processing.alter_metadata.input_value.display_name'),
            info=i18n.t(
                'components.processing.alter_metadata.input_value.info'),
            required=False,
            input_types=["Message", "Data"],
            is_list=True,
        ),
        StrInput(
            name="text_in",
            display_name=i18n.t(
                'components.processing.alter_metadata.text_in.display_name'),
            info=i18n.t('components.processing.alter_metadata.text_in.info'),
            required=False,
        ),
        NestedDictInput(
            name="metadata",
            display_name=i18n.t(
                'components.processing.alter_metadata.metadata.display_name'),
            info=i18n.t('components.processing.alter_metadata.metadata.info'),
            input_types=["Data"],
            required=True,
        ),
        MessageTextInput(
            name="remove_fields",
            display_name=i18n.t(
                'components.processing.alter_metadata.remove_fields.display_name'),
            info=i18n.t(
                'components.processing.alter_metadata.remove_fields.info'),
            required=False,
            is_list=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t(
                'components.processing.alter_metadata.outputs.data.display_name'),
            info=i18n.t(
                'components.processing.alter_metadata.outputs.data.info'),
            method="process_output",
        ),
        Output(
            display_name=i18n.t(
                'components.processing.alter_metadata.outputs.dataframe.display_name'),
            name="dataframe",
            info=i18n.t(
                'components.processing.alter_metadata.outputs.dataframe.info'),
            method="as_dataframe",
        ),
    ]

    def _as_clean_dict(self, obj):
        """Convert a Data object or a standard dictionary to a standard dictionary."""
        try:
            if isinstance(obj, dict):
                as_dict = obj
            elif isinstance(obj, Data):
                as_dict = obj.data
            else:
                error_msg = i18n.t('components.processing.alter_metadata.errors.invalid_object_type',
                                   obj_type=type(obj).__name__)
                raise TypeError(error_msg)

            return {k: v for k, v in (as_dict or {}).items() if k and k.strip()}

        except Exception as e:
            error_msg = i18n.t('components.processing.alter_metadata.errors.dict_conversion_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def process_output(self) -> list[Data]:
        try:
            # Ensure metadata is a dictionary, filtering out any empty keys
            if not self.metadata:
                warning_msg = i18n.t(
                    'components.processing.alter_metadata.warnings.empty_metadata')
                self.status = warning_msg

            metadata = self._as_clean_dict(
                self.metadata) if self.metadata else {}

            # Convert text_in to a Data object if it exists, and initialize our list of Data objects
            data_objects = []
            if self.text_in and self.text_in.strip():
                data_objects.append(Data(text=self.text_in.strip()))

            # Append existing Data objects from input_value, if any
            if self.input_value:
                data_objects.extend(self.input_value)

            if not data_objects:
                warning_msg = i18n.t(
                    'components.processing.alter_metadata.warnings.no_input_data')
                self.status = warning_msg
                return []

            # Update each Data object with the new metadata, preserving existing fields
            if metadata:
                for data in data_objects:
                    data.data.update(metadata)

            # Handle removal of fields specified in remove_fields
            if self.remove_fields:
                fields_to_remove = {
                    field.strip() for field in self.remove_fields if field and field.strip()}

                if fields_to_remove:
                    removed_count = 0
                    # Remove specified fields from each Data object's metadata
                    for data in data_objects:
                        original_keys = set(data.data.keys())
                        data.data = {
                            k: v for k, v in data.data.items() if k not in fields_to_remove}
                        removed_count += len(original_keys -
                                             set(data.data.keys()))

                    if removed_count > 0:
                        info_msg = i18n.t('components.processing.alter_metadata.info.fields_removed',
                                          count=removed_count, fields=', '.join(fields_to_remove))
                        self.log(info_msg)

            # Set the status for tracking/debugging purposes
            success_msg = i18n.t('components.processing.alter_metadata.success.metadata_processed',
                                 count=len(data_objects))
            self.status = success_msg

            return data_objects

        except TypeError:
            # Re-raise TypeError as is (already has i18n message)
            raise
        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t('components.processing.alter_metadata.errors.processing_failed',
                               error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def as_dataframe(self) -> DataFrame:
        """Convert the processed data objects into a DataFrame.

        Returns:
            DataFrame: A DataFrame where each row corresponds to a Data object,
                    with metadata fields as columns.
        """
        try:
            data_list = self.process_output()

            if not data_list:
                warning_msg = i18n.t(
                    'components.processing.alter_metadata.warnings.empty_dataframe')
                self.status = warning_msg
                return DataFrame([])

            dataframe = DataFrame(data_list)
            success_msg = i18n.t('components.processing.alter_metadata.success.dataframe_created',
                                 rows=len(data_list))
            self.status = success_msg

            return dataframe

        except Exception as e:
            error_msg = i18n.t('components.processing.alter_metadata.errors.dataframe_creation_failed',
                               error=str(e))
            self.status = error_msg
            return DataFrame([])
