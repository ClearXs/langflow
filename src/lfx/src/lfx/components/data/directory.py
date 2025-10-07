import i18n
from lfx.base.data.utils import TEXT_FILE_TYPES, parallel_load_data, parse_text_file_to_data, retrieve_file_paths
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, MessageTextInput, MultiselectInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.template.field.base import Output


class DirectoryComponent(Component):
    display_name = i18n.t('components.data.directory.display_name')
    description = i18n.t('components.data.directory.description')
    documentation: str = "https://docs.langflow.org/components-data#directory"
    icon = "folder"
    name = "Directory"

    inputs = [
        MessageTextInput(
            name="path",
            display_name=i18n.t('components.data.directory.path.display_name'),
            info=i18n.t('components.data.directory.path.info'),
            value=".",
            tool_mode=True,
        ),
        MultiselectInput(
            name="types",
            display_name=i18n.t(
                'components.data.directory.types.display_name'),
            info=i18n.t('components.data.directory.types.info'),
            options=TEXT_FILE_TYPES,
            value=[],
        ),
        IntInput(
            name="depth",
            display_name=i18n.t(
                'components.data.directory.depth.display_name'),
            info=i18n.t('components.data.directory.depth.info'),
            value=0,
        ),
        IntInput(
            name="max_concurrency",
            display_name=i18n.t(
                'components.data.directory.max_concurrency.display_name'),
            advanced=True,
            info=i18n.t('components.data.directory.max_concurrency.info'),
            value=2,
        ),
        BoolInput(
            name="load_hidden",
            display_name=i18n.t(
                'components.data.directory.load_hidden.display_name'),
            advanced=True,
            info=i18n.t('components.data.directory.load_hidden.info'),
        ),
        BoolInput(
            name="recursive",
            display_name=i18n.t(
                'components.data.directory.recursive.display_name'),
            advanced=True,
            info=i18n.t('components.data.directory.recursive.info'),
        ),
        BoolInput(
            name="silent_errors",
            display_name=i18n.t(
                'components.data.directory.silent_errors.display_name'),
            advanced=True,
            info=i18n.t('components.data.directory.silent_errors.info'),
        ),
        BoolInput(
            name="use_multithreading",
            display_name=i18n.t(
                'components.data.directory.use_multithreading.display_name'),
            advanced=True,
            info=i18n.t('components.data.directory.use_multithreading.info'),
        ),
    ]

    outputs = [
        Output(display_name=i18n.t('components.data.directory.outputs.dataframe.display_name'),
               name="dataframe", method="as_dataframe"),
    ]

    def load_directory(self) -> list[Data]:
        path = self.path
        types = self.types
        depth = self.depth
        max_concurrency = self.max_concurrency
        load_hidden = self.load_hidden
        recursive = self.recursive
        silent_errors = self.silent_errors
        use_multithreading = self.use_multithreading

        resolved_path = self.resolve_path(path)

        # If no types are specified, use all supported types
        if not types:
            types = TEXT_FILE_TYPES

        # Check if all specified types are valid
        invalid_types = [t for t in types if t not in TEXT_FILE_TYPES]
        if invalid_types:
            msg = i18n.t('components.data.directory.errors.invalid_file_types',
                         invalid_types=str(invalid_types), valid_types=str(TEXT_FILE_TYPES))
            raise ValueError(msg)

        valid_types = types

        file_paths = retrieve_file_paths(
            resolved_path, load_hidden=load_hidden, recursive=recursive, depth=depth, types=valid_types
        )

        loaded_data = []
        if use_multithreading:
            loaded_data = parallel_load_data(
                file_paths, silent_errors=silent_errors, max_concurrency=max_concurrency)
        else:
            loaded_data = [parse_text_file_to_data(
                file_path, silent_errors=silent_errors) for file_path in file_paths]

        valid_data = [
            x for x in loaded_data if x is not None and isinstance(x, Data)]
        self.status = valid_data
        return valid_data

    def as_dataframe(self) -> DataFrame:
        return DataFrame(self.load_directory())
